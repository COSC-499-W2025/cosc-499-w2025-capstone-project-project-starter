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
from src.worker.workspace import fetch_snapshot_files, materialize_snapshot_to_dir


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

                # Find existing contributor (best-effort match)
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
