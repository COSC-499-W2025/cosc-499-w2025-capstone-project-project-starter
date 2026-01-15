from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.codeparser.file_classification import is_binary_file 
from src.codeparser.chunking import EXT_TO_LANG, chunk as chunk_text
from src.contributions.contribution_check import find_git_repos, get_commit_contributions
from src.worker.workspace import materialize_snapshot_to_dir
from src.db.base import fetch_snapshot_files

import json
import math
import numpy as np

from src.ml.universal import predict as ml_predict
from src.codeparser.chunking import chunk as chunk_text

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
    """
    Produces lightweight, reliable signals without invoking ML:
      - total/text/binary counts (via libmagic)
      - language counts (via extension mapping)
      - activity breakdown (code/test/document/design/other)
      - chunk counts (approximate) for text files using chunking.chunk()
    """
    files = fetch_snapshot_files(engine, snapshot_id)

    total_files = len(files)
    size_total = sum(f.size_bytes for f in files)

    language_counts = Counter()
    activity_counts = Counter()
    binary_count = 0
    text_count = 0
    chunks_total = 0
    chunks_by_lang = Counter()

    # Evaluate using stored blob paths (no need to materialize snapshot)
    for f in files:
        lang = _infer_language_from_relpath(f.relative_path)
        language_counts[lang] += 1
        activity_counts[_classify_activity(f.relative_path)] += 1

        # binary/text distinction using libmagic
        is_bin = True
        try:
            is_bin = is_binary_file(f.stored_path)
        except Exception:
            is_bin = True

        if is_bin:
            binary_count += 1
            continue

        text_count += 1

        # chunk count using codeparser.chunking.chunk()
        try:
            with open(f.stored_path, "r", encoding="utf-8", errors="replace") as fp:
                s = fp.read(1_000_000)
            # chunk_text yields (start,end,textslice)
            c = sum(1 for _ in chunk_text(s))
            chunks_total += c
            chunks_by_lang[lang] += c
        except Exception:
            # ignore unreadable text files
            pass

    # Top languages by file count
    top_languages = [{"language": k, "files": v} for k, v in language_counts.most_common(10)]

    return {
        "snapshot_id": snapshot_id,
        "generated_at": _utcnow_iso(),
        "totals": {
            "files": total_files,
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


def _parse_author_key(author_key: str) -> Tuple[str, str | None]:
    # "Name <email>"
    m = re.match(r"^(.*?)(?:\s*<([^>]+)>)?$", author_key.strip())
    if not m:
        return author_key.strip(), None
    name = (m.group(1) or "").strip() or author_key.strip()
    email = (m.group(2) or "").strip() or None
    return name, email


def run_git_metrics(engine: Engine, snapshot_id: str) -> Dict[str, Any]:
    """
    If the snapshot contains one or more .git directories, compute commit counts per author
    and store normalized data in contributors/project_contributors/contribution_events.

    If there are no git repos present in the snapshot, returns a result stating that.
    """
    files = fetch_snapshot_files(engine, snapshot_id)
    workdir = materialize_snapshot_to_dir(files)

    try:
        repos = find_git_repos(workdir)
        repo_count = len(repos)

        # Map snapshot -> project_id for contribution tables
        with engine.connect() as conn:
            project_id = conn.execute(
                text("SELECT project_id FROM snapshots WHERE id = :sid"),
                {"sid": snapshot_id},
            ).scalar_one()

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

        # Persist to DB
        with engine.begin() as conn:
            for author_key, commit_count in all_contribs.items():
                name, email = _parse_author_key(author_key)

                # Find existing contributor
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

                # Link contributor to project (is_user left FALSE; can be set later via config/UI)
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

                # Insert contribution event (activity_type=code; other counts unknown for now)
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

        return {
            "snapshot_id": snapshot_id,
            "generated_at": _utcnow_iso(),
            "git_repos_found": repo_count,
            "repo_summaries": repo_summaries,
            "commit_contributions": all_contribs,
        }
    finally:
        # Cleanup workdir
        try:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass

def run_local_ml(engine: Engine, analysis_id: str, snapshot_id: str) -> Dict[str, Any]:
    """
    Always-run local ML analysis:
      - reads all non-binary files from blobstore paths
      - chunks text (windowed) and runs batched embeddings + logistic regression
      - aggregates across chunks/files
      - writes normalized rows into skills + analysis_skills
      - returns a structured output_json payload
    """
    threshold = float(os.environ.get("LOCAL_ML_THRESHOLD", "0.5"))
    max_file_chars = int(os.environ.get("LOCAL_ML_MAX_FILE_CHARS", "1000000"))
    max_chunks_total = int(os.environ.get("LOCAL_ML_MAX_CHUNKS_TOTAL", "5000"))
    embed_batch = int(os.environ.get("LOCAL_ML_EMBED_BATCH", "16"))

    files = fetch_snapshot_files(engine, snapshot_id)

    # Load model resources once (tokenizer, encoder, classifier, skill names).
    ml_predict._load_resources()
    skill_names: List[str] = list(ml_predict._skills)
    n_skills = len(skill_names)

    # Aggregates
    max_prob = np.zeros(n_skills, dtype=np.float32)
    sum_prob = np.zeros(n_skills, dtype=np.float32)
    hit_count = np.zeros(n_skills, dtype=np.int32)
    first_seen = [None] * n_skills  # datetime or None
    examples = [[] for _ in range(n_skills)]  # list of {"path","p","ts"}

    total_chunks = 0
    text_files = 0
    binary_files = 0

    def maybe_record_example(i: int, relpath: str, p: float, ts):
        ex = examples[i]
        ex.append({"path": relpath, "p": float(p), "ts": ts.isoformat() if ts else None})
        ex.sort(key=lambda r: r["p"], reverse=True)
        del ex[3:]  # keep top 3

    batch_texts: List[str] = []
    batch_meta: List[Tuple[str, Any]] = []  # (relpath, last_modified_ts)

    def flush_batch():
        nonlocal batch_texts, batch_meta
        if not batch_texts:
            return

        X = ml_predict.embed_texts(batch_texts, ml_predict._tok, ml_predict._enc, ml_predict._device)
        probs = ml_predict._clf.predict_proba(X)  # shape (B, n_skills)

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
        # skip binary
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

        # Chunk into model window size. predict.py truncates to 2000 chars anyway,
        # but chunking is essential for coverage. :contentReference[oaicite:4]{index=4}
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

    # Build final ranked results
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

    # Persist normalization: skills + analysis_skills
    with engine.begin() as conn:
        # Clear any previous run for this analysis row
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

            # Store evidence in a compact json
            evidence = {
                "hits": row["hits"],
                "avg_prob": row["avg_prob"],
                "max_prob": row["max_prob"],
                "examples": row["examples"],
            }

            # Prefer first_seen_ts column if present; otherwise store only in evidence_json.
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

    return output
