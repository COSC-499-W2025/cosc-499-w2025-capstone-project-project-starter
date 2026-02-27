from __future__ import annotations

import os
import re
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

import json
import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.codeparser.file_classification import is_binary_file
from src.codeparser.chunking import EXT_TO_LANG, chunk as chunk_text
from src.worker.contribution_check import find_git_repos, get_commit_contributions
from src.worker.workspace import materialize_snapshot_to_dir
from src.db.base import fetch_snapshot_files
from src.db.consents import get_snapshot_owner_user_id, is_external_services_allowed

from src.ml import predict as ml_predict
from src.worker.llm import run_external_llm_analysis

from src.db.user_config import identity_rules_for_user

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_language_from_relpath(relpath: str) -> str:
    _, ext = os.path.splitext(relpath)
    return EXT_TO_LANG.get(ext.lower(), "unknown")


def _classify_activity(relpath: str) -> str:
    p = relpath.lower().replace("\\", "/")
    if re.search(r"test_|_test\.|/tests?/", p):
        return "test"
    if p.endswith((".py", ".js", ".java", ".cpp", ".c", ".ts", ".rs", ".go", ".kt", ".cs")):
        return "code"
    if p.endswith((".md", ".txt", ".rst", ".pdf")):
        return "document"
    if p.endswith((".drawio", ".png", ".jpg", ".jpeg", ".svg")):
        return "design"
    return "other"


def run_parser(engine: Engine, snapshot_id: str) -> Dict[str, Any]:
    files = fetch_snapshot_files(engine, snapshot_id)
    logger.info("Running parser analysis for snapshot %s (%d files)", snapshot_id, len(files))

    total_files = len(files)
    size_total = sum(f.size_bytes for f in files)
    total_lines = 0

    language_counts = Counter()
    activity_counts = Counter()
    binary_count = 0
    text_count = 0
    chunks_total = 0
    chunks_by_lang = Counter()

    for f in files:
        lang = _infer_language_from_relpath(f.relative_path)
        language_counts[lang] += 1
        activity_counts[_classify_activity(f.relative_path)] += 1

        is_bin = True
        try:
            is_bin = is_binary_file(f.stored_path)
        except Exception:
            is_bin = True

        if is_bin:
            binary_count += 1
            continue

        text_count += 1
        try:
            captured_parts: List[str] = []
            captured_chars = 0
            line_count = 0

            with open(f.stored_path, "r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    line_count += 1
                    if captured_chars >= 1_000_000:
                        continue

                    remaining = 1_000_000 - captured_chars
                    if len(line) <= remaining:
                        captured_parts.append(line)
                        captured_chars += len(line)
                    else:
                        captured_parts.append(line[:remaining])
                        captured_chars = 1_000_000

            total_lines += line_count
            s = "".join(captured_parts)
            c = sum(1 for _ in chunk_text(s))
            chunks_total += c
            chunks_by_lang[lang] += c
        except Exception:
            pass

    top_languages = [{"language": k, "files": v} for k, v in language_counts.most_common(10)]

    output = {
        "snapshot_id": snapshot_id,
        "generated_at": _utcnow_iso(),
        "totals": {
            "files": total_files,
            "total_lines": total_lines,
            "lines": total_lines,
            "bytes": size_total,
            "text_files": text_count,
            "binary_files": binary_count,
            "text_chunks": chunks_total,
        },
        "language_counts": dict(language_counts),
        "activity_counts": dict(activity_counts),
        "chunks_by_language": dict(chunks_by_lang),
        "top_languages": top_languages,
    }
    logger.info(
        "Parser analysis complete for snapshot %s (text_files=%d binary_files=%d total_lines=%d)",
        snapshot_id,
        text_count,
        binary_count,
        total_lines,
    )
    return output


def _parse_author_key(author_key: str) -> Tuple[str, str | None]:
    m = re.match(r"^(.*?)(?:\s*<([^>]+)>)?$", author_key.strip())
    if not m:
        return author_key.strip(), None
    name = (m.group(1) or "").strip() or author_key.strip()
    email = (m.group(2) or "").strip() or None
    return name, email


def _auto_flag_user_contributor(
    conn,
    *,
    project_id: str,
    user_id: str,
    author_rows: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Uses user_config.identity to deterministically set project_contributors.is_user:
      1) If identity.project_contributor_map has project_id -> contributor_id, choose it.
      2) Else, match by email/name rules; if multiple matches, choose highest-commits.
    Returns chosen contributor_id or None.
    """
    match_emails, match_names, mapping = identity_rules_for_user(conn, user_id)

    mapped = mapping.get(str(project_id))
    if mapped:
        # Ensure only this one is_user.
        conn.execute(
            text("UPDATE project_contributors SET is_user = FALSE WHERE project_id = :pid"),
            {"pid": project_id},
        )
        conn.execute(
            text(
                """
                UPDATE project_contributors
                SET is_user = TRUE
                WHERE project_id = :pid AND contributor_id = :cid
                """
            ),
            {"pid": project_id, "cid": mapped},
        )
        return str(mapped)

    # Normalize rules for case-insensitive match.
    email_set = {e.strip().casefold() for e in match_emails if str(e).strip()}
    name_set = {n.strip().casefold() for n in match_names if str(n).strip()}

    if not email_set and not name_set:
        return None

    candidates: List[Tuple[int, str]] = []
    for r in author_rows:
        cid = str(r["contributor_id"])
        commits = int(r.get("commits") or 0)
        nm = (r.get("canonical_name") or "")
        em = (r.get("email") or "")

        nm_cf = str(nm).strip().casefold()
        em_cf = str(em).strip().casefold()

        if em_cf and em_cf in email_set:
            candidates.append((commits, cid))
            continue
        if nm_cf and nm_cf in name_set:
            candidates.append((commits, cid))
            continue

    if not candidates:
        return None

    # Choose highest-commits; stable tie-breaker by UUID string.
    candidates.sort(key=lambda t: (-int(t[0]), str(t[1])))
    chosen = str(candidates[0][1])

    conn.execute(
        text("UPDATE project_contributors SET is_user = FALSE WHERE project_id = :pid"),
        {"pid": project_id},
    )
    conn.execute(
        text(
            """
            UPDATE project_contributors
            SET is_user = TRUE
            WHERE project_id = :pid AND contributor_id = :cid
            """
        ),
        {"pid": project_id, "cid": chosen},
    )
    return chosen



def run_git_metrics(engine: Engine, snapshot_id: str) -> Dict[str, Any]:
    files = fetch_snapshot_files(engine, snapshot_id)
    workdir = materialize_snapshot_to_dir(files)
    logger.info("Running git_metrics analysis for snapshot %s", snapshot_id)

    try:
        repos = find_git_repos(workdir)
        repo_count = len(repos)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT s.project_id, p.user_id
                    FROM snapshots s
                    JOIN projects pr ON pr.id = s.project_id
                    JOIN portfolios p ON p.id = pr.portfolio_id
                    WHERE s.id = :sid
                    """
                ),
                {"sid": snapshot_id},
            ).mappings().first()
            project_id = str(row["project_id"]) if row else None
            owner_user_id = str(row["user_id"]) if row and row.get("user_id") else None

        if not project_id:
            raise RuntimeError("could not resolve project_id for snapshot")

        all_contribs: Dict[str, int] = {}
        repo_summaries: List[Dict[str, Any]] = []

        for repo_path in repos:
            contribs = get_commit_contributions(repo_path)
            repo_summaries.append(
                {
                    "repo_path": str(repo_path),
                    "authors": len(contribs),
                    "total_commits": int(sum(contribs.values())),
                }
            )
            for k, v in contribs.items():
                all_contribs[k] = all_contribs.get(k, 0) + int(v)

        author_rows_for_matching: List[Dict[str, Any]] = []

        with engine.begin() as conn:
            # Insert contributors + project_contributors + contribution_events
            for author_key, commit_count in all_contribs.items():
                name, email = _parse_author_key(author_key)

                cid = conn.execute(
                    text(
                        """
                        SELECT id FROM contributors
                        WHERE canonical_name = :name AND (email = :email OR (:email IS NULL AND email IS NULL))
                        ORDER BY id ASC LIMIT 1
                        """
                    ),
                    {"name": name, "email": email},
                ).scalar()

                if not cid:
                    cid = conn.execute(
                        text(
                            """
                            INSERT INTO contributors (canonical_name, email)
                            VALUES (:name, :email)
                            RETURNING id
                            """
                        ),
                        {"name": name, "email": email},
                    ).scalar_one()

                conn.execute(
                    text(
                        """
                        INSERT INTO project_contributors (project_id, contributor_id, is_user)
                        VALUES (:pid, :cid, FALSE)
                        ON CONFLICT (project_id, contributor_id) DO NOTHING
                        """
                    ),
                    {"pid": project_id, "cid": cid},
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO contribution_events
                          (snapshot_id, contributor_id, activity_type, commit_count, file_change_count, lines_added, lines_deleted)
                        VALUES
                          (:sid, :cid, 'code', :commits, 0, 0, 0)
                        """
                    ),
                    {"sid": snapshot_id, "cid": cid, "commits": int(commit_count)},
                )

                author_rows_for_matching.append(
                    {
                        "contributor_id": str(cid),
                        "canonical_name": name,
                        "email": email,
                        "commits": int(commit_count),
                    }
                )

            # D) Auto-link user identity when rules exist in user_config (deterministic).
            if owner_user_id:
                _auto_flag_user_contributor(
                    conn,
                    project_id=project_id,
                    user_id=owner_user_id,
                    author_rows=author_rows_for_matching,
                )

            # Make collaboration_type authoritative in DB after git_metrics runs.
            # Use project_contributors count (across all snapshots) as the authoritative source of distinct contributors.
            contributor_count = int(
                conn.execute(
                    text("SELECT COUNT(*) FROM project_contributors WHERE project_id = :pid"),
                    {"pid": project_id},
                ).scalar_one()
            )
            collab_type = "collaborative" if contributor_count > 1 else "individual"

            conn.execute(
                text(
                    """
                    UPDATE projects
                    SET collaboration_type = :ctype
                    WHERE id = :pid
                    """
                ),
                {"ctype": collab_type, "pid": project_id},
            )

        output = {
            "snapshot_id": snapshot_id,
            "generated_at": _utcnow_iso(),
            "git_repos_found": repo_count,
            "repo_summaries": repo_summaries,
            "commit_contributions": all_contribs,
            "derived": {
                "project_id": str(project_id),
                "distinct_contributors": int(len(all_contribs)),
                "authoritative_collaboration_type": collab_type,
            },
        }
        logger.info(
            "git_metrics complete for snapshot %s (repos=%d contributors=%d)",
            snapshot_id,
            repo_count,
            len(all_contribs),
        )
        return output
    finally:
        try:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            logger.warning("Failed to clean temporary git_metrics workspace %s", workdir, exc_info=True)

def run_local_ml(engine: Engine, analysis_id: str, snapshot_id: str) -> Dict[str, Any]:
    threshold = float(os.environ.get("LOCAL_ML_THRESHOLD", "0.5"))
    max_file_chars = int(os.environ.get("LOCAL_ML_MAX_FILE_CHARS", "1000000"))
    max_chunks_total = int(os.environ.get("LOCAL_ML_MAX_CHUNKS_TOTAL", "5000"))
    embed_batch = int(os.environ.get("LOCAL_ML_EMBED_BATCH", "16"))

    files = fetch_snapshot_files(engine, snapshot_id)
    logger.info("Running local_ml analysis for snapshot %s", snapshot_id)

    ml_predict._load_resources()
    skill_names: List[str] = list(ml_predict._skills)
    n_skills = len(skill_names)

    max_prob = np.zeros(n_skills, dtype=np.float32)
    sum_prob = np.zeros(n_skills, dtype=np.float32)
    hit_count = np.zeros(n_skills, dtype=np.int32)
    first_seen = [None] * n_skills
    examples = [[] for _ in range(n_skills)]

    total_chunks = 0
    text_files = 0
    binary_files = 0

    def maybe_record_example(i: int, relpath: str, p: float, ts):
        ex = examples[i]
        ex.append({"path": relpath, "p": float(p), "ts": ts.isoformat() if ts else None})
        ex.sort(key=lambda r: r["p"], reverse=True)
        del ex[3:]

    batch_texts: List[str] = []
    batch_meta: List[Tuple[str, Any]] = []

    def flush_batch():
        nonlocal batch_texts, batch_meta
        if not batch_texts:
            return

        X = ml_predict.embed_texts(batch_texts, ml_predict._tok, ml_predict._enc, ml_predict._device)
        probs = ml_predict._clf.predict_proba(X)

        for j in range(probs.shape[0]):
            relpath, ts = batch_meta[j]
            row = probs[j]
            idxs = np.where(row >= threshold)[0]
            if idxs.size == 0:
                continue

            for i in idxs.tolist():
                p = float(row[i])
                hit_count[i] += 1
                sum_prob[i] += p
                if p > float(max_prob[i]):
                    max_prob[i] = p

                if ts is not None:
                    cur = first_seen[i]
                    if cur is None or ts < cur:
                        first_seen[i] = ts

                maybe_record_example(i, relpath, p, ts)

        batch_texts = []
        batch_meta = []

    for f in files:
        try:
            if is_binary_file(f.stored_path):
                binary_files += 1
                continue
        except Exception:
            binary_files += 1
            continue

        text_files += 1

        try:
            with open(f.stored_path, "r", encoding="utf-8", errors="replace") as fp:
                raw = fp.read(max_file_chars)
        except Exception:
            continue

        for _start, _end, slice_ in chunk_text(raw):
            if not slice_:
                continue
            batch_texts.append(slice_)
            batch_meta.append((f.relative_path, f.last_modified_ts))
            total_chunks += 1

            if len(batch_texts) >= embed_batch:
                flush_batch()

            if total_chunks >= max_chunks_total:
                break

        if total_chunks >= max_chunks_total:
            break

    flush_batch()

    detected = np.where(hit_count > 0)[0]
    skills_out = []
    for i in detected.tolist():
        avg = float(sum_prob[i] / max(1, int(hit_count[i])))
        skills_out.append(
            {
                "skill": skill_names[i],
                "max_prob": float(max_prob[i]),
                "avg_prob": avg,
                "hits": int(hit_count[i]),
                "first_seen_ts": first_seen[i].isoformat() if first_seen[i] else None,
                "examples": examples[i],
            }
        )
    skills_out.sort(key=lambda r: (r["max_prob"], r["hits"]), reverse=True)

    output = {
        "snapshot_id": snapshot_id,
        "generated_at": _utcnow_iso(),
        "threshold": threshold,
        "limits": {
            "max_file_chars": max_file_chars,
            "max_chunks_total": max_chunks_total,
            "embed_batch": embed_batch,
        },
        "totals": {
            "files": len(files),
            "text_files": int(text_files),
            "binary_files": int(binary_files),
            "chunks_scored": int(total_chunks),
            "skills_detected": int(len(skills_out)),
        },
        "skills": skills_out[:200],
    }

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM analysis_skills WHERE analysis_id = :aid"), {"aid": analysis_id})

        for row in skills_out:
            name = row["skill"]
            category = name.split("-", 1)[0] if "-" in name else None

            conn.execute(
                text(
                    """
                    INSERT INTO skills (skill_name, category)
                    VALUES (:name, :cat)
                    ON CONFLICT (skill_name) DO NOTHING
                    """
                ),
                {"name": name, "cat": category},
            )

            sid = conn.execute(text("SELECT id FROM skills WHERE skill_name = :name"), {"name": name}).scalar_one()

            evidence = {
                "hits": row["hits"],
                "avg_prob": row["avg_prob"],
                "max_prob": row["max_prob"],
                "examples": row["examples"],
            }

            cols = conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'analysis_skills'
                    """
                )
            ).scalars().all()
            colset = set(cols)

            if "first_seen_ts" in colset and "evidence_json" in colset:
                conn.execute(
                    text(
                        """
                        INSERT INTO analysis_skills (analysis_id, skill_id, confidence, first_seen_ts, evidence_json)
                        VALUES (:aid, :sid, :conf, :fst, CAST(:ev AS jsonb))
                        """
                    ),
                    {
                        "aid": analysis_id,
                        "sid": sid,
                        "conf": float(row["max_prob"]),
                        "fst": row["first_seen_ts"],
                        "ev": json.dumps(evidence),
                    },
                )
            elif "evidence_json" in colset:
                conn.execute(
                    text(
                        """
                        INSERT INTO analysis_skills (analysis_id, skill_id, confidence, evidence_json)
                        VALUES (:aid, :sid, :conf, CAST(:ev AS jsonb))
                        """
                    ),
                    {"aid": analysis_id, "sid": sid, "conf": float(row["max_prob"]), "ev": json.dumps(evidence)},
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO analysis_skills (analysis_id, skill_id, confidence)
                        VALUES (:aid, :sid, :conf)
                        """
                    ),
                    {"aid": analysis_id, "sid": sid, "conf": float(row["max_prob"])},
                )

    logger.info(
        "local_ml complete for snapshot %s (chunks_scored=%d skills_detected=%d)",
        snapshot_id,
        total_chunks,
        len(skills_out),
    )
    return output


def run_external_llm(engine: Engine, analysis_id: str, snapshot_id: str) -> Dict[str, Any]:
    logger.info("Running external_llm analysis for snapshot %s", snapshot_id)
    with engine.connect() as conn:
        uid = get_snapshot_owner_user_id(conn, snapshot_id)
        if not uid:
            fallback = run_local_ml(engine, analysis_id, snapshot_id)
            fallback["external_llm"] = {"used": "local_ml", "reason": "snapshot owner could not be resolved"}
            logger.warning(
                "external_llm fallback to local_ml for snapshot %s: snapshot owner unresolved",
                snapshot_id,
            )
            return fallback

        allowed = is_external_services_allowed(conn, str(uid))

    if not allowed:
        fallback = run_local_ml(engine, analysis_id, snapshot_id)
        fallback["external_llm"] = {"used": "local_ml", "reason": "external_services consent not granted"}
        logger.warning(
            "external_llm fallback to local_ml for snapshot %s: external services consent not granted",
            snapshot_id,
        )
        return fallback

    out = run_external_llm_analysis(engine, snapshot_id)
    out["external_llm"] = {"used": "ollama"}
    logger.info("external_llm complete for snapshot %s", snapshot_id)
    return out
