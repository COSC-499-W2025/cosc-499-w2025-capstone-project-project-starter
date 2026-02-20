from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Connection, Engine


@dataclass(frozen=True)
class BlobDeleteResult:
    deleted_sha256: str
    stored_path: str


def _gc_unreferenced_blobs(conn: Connection, candidate_shas: List[str]) -> List[BlobDeleteResult]:
    """
    Garbage-collect file_blobs that are no longer referenced by:
      - snapshot_files.file_sha256
      - portfolio_showcases.thumbnail_blob_sha256
    This is the key safety property: shared blobs remain if still referenced elsewhere.
    """
    shas = [s for s in (candidate_shas or []) if isinstance(s, str) and len(s) == 64]
    if not shas:
        return []

    stmt = text(
        """
        SELECT b.sha256, b.stored_path
        FROM file_blobs b
        WHERE b.sha256 = ANY(:shas)
          AND NOT EXISTS (SELECT 1 FROM snapshot_files sf WHERE sf.file_sha256 = b.sha256)
          AND NOT EXISTS (SELECT 1 FROM portfolio_showcases ps WHERE ps.thumbnail_blob_sha256 = b.sha256)
        """
    ).bindparams(bindparam("shas", type_=ARRAY(String())))

    rows = conn.execute(stmt, {"shas": shas}).mappings().all()
    if not rows:
        return []

    deletable = [str(r["sha256"]) for r in rows]
    del_stmt = text(
        """
        DELETE FROM file_blobs
        WHERE sha256 = ANY(:shas)
        """
    ).bindparams(bindparam("shas", type_=ARRAY(String())))

    # Delete DB rows first; file deletion happens after commit.
    conn.execute(del_stmt, {"shas": deletable})

    out: List[BlobDeleteResult] = []
    for r in rows:
        out.append(BlobDeleteResult(deleted_sha256=str(r["sha256"]), stored_path=str(r["stored_path"])))
    return out


def _delete_paths_best_effort(paths: List[str]) -> int:
    deleted = 0
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.unlink(p)
                deleted += 1
        except Exception:
            # Best effort. DB is already correct; filesystem cleanup should not break API semantics.
            pass
    return deleted


def delete_snapshot_and_gc(engine: Engine, snapshot_id: str) -> Dict:
    """
    Deletes a snapshot (and cascades: analyses, contribution_events, snapshot_files),
    then garbage-collects any now-unreferenced blobs previously used by that snapshot.
    """
    snapshot_id = str(snapshot_id)

    blob_paths: List[str] = []
    blob_deleted_rows: List[BlobDeleteResult] = []

    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM snapshots WHERE id = :sid"), {"sid": snapshot_id}).scalar()
        if not exists:
            raise KeyError("snapshot_not_found")

        # Capture candidate blob shas before cascade deletes snapshot_files.
        shas = [
            str(x)
            for x in conn.execute(
                text("SELECT DISTINCT file_sha256 FROM snapshot_files WHERE snapshot_id = :sid"),
                {"sid": snapshot_id},
            ).scalars().all()
        ]

        # Delete snapshot (CASCADE removes snapshot_files, analyses, contribution_events).
        conn.execute(text("DELETE FROM snapshots WHERE id = :sid"), {"sid": snapshot_id})

        # GC only those blobs that are now unreferenced anywhere else.
        blob_deleted_rows = _gc_unreferenced_blobs(conn, shas)
        blob_paths = [r.stored_path for r in blob_deleted_rows]

    # After commit, delete blob files from disk best-effort.
    fs_deleted = _delete_paths_best_effort(blob_paths)

    return {
        "snapshot_id": snapshot_id,
        "deleted": True,
        "gc": {
            "candidate_shas": int(len(set(blob_paths))) if blob_paths else 0,
            "blobs_deleted": len(blob_deleted_rows),
            "files_deleted_from_disk": int(fs_deleted),
            "deleted_sha256": [r.deleted_sha256 for r in blob_deleted_rows],
        },
    }


def delete_portfolio_showcase_and_gc(engine: Engine, showcase_id: str) -> Dict:
    """
    Deletes a portfolio_showcases row. If it referenced a thumbnail blob, GC it if unreferenced elsewhere.
    """
    showcase_id = str(showcase_id)
    blob_paths: List[str] = []
    blob_deleted_rows: List[BlobDeleteResult] = []

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, thumbnail_blob_sha256
                FROM portfolio_showcases
                WHERE id = :id
                """
            ),
            {"id": showcase_id},
        ).mappings().first()

        if not row:
            raise KeyError("showcase_not_found")

        thumb = row.get("thumbnail_blob_sha256")
        conn.execute(text("DELETE FROM portfolio_showcases WHERE id = :id"), {"id": showcase_id})

        if thumb:
            blob_deleted_rows = _gc_unreferenced_blobs(conn, [str(thumb)])
            blob_paths = [r.stored_path for r in blob_deleted_rows]

    fs_deleted = _delete_paths_best_effort(blob_paths)

    return {
        "showcase_id": showcase_id,
        "deleted": True,
        "thumbnail_gc": {
            "attempted": bool(row.get("thumbnail_blob_sha256") is not None),
            "blobs_deleted": len(blob_deleted_rows),
            "files_deleted_from_disk": int(fs_deleted),
            "deleted_sha256": [r.deleted_sha256 for r in blob_deleted_rows],
        },
    }


def delete_resume_item(engine: Engine, resume_id: str) -> Dict:
    resume_id = str(resume_id)
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM resume_items WHERE id = :id"), {"id": resume_id}).scalar()
        if not exists:
            raise KeyError("resume_not_found")
        conn.execute(text("DELETE FROM resume_items WHERE id = :id"), {"id": resume_id})
    return {"resume_id": resume_id, "deleted": True}


def delete_analysis(engine: Engine, analysis_id: str) -> Dict:
    analysis_id = str(analysis_id)
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM analyses WHERE id = :id"), {"id": analysis_id}).scalar()
        if not exists:
            raise KeyError("analysis_not_found")
        conn.execute(text("DELETE FROM analyses WHERE id = :id"), {"id": analysis_id})
    return {"analysis_id": analysis_id, "deleted": True}


def delete_project_and_gc(engine: Engine, project_id: str) -> Dict:
    """
    Deletes a project (and cascades all dependent rows), then garbage-collects
    any now-unreferenced file blobs that belonged to the project's snapshots
    or showcase thumbnail.
    """
    project_id = str(project_id)

    blob_paths: List[str] = []
    blob_deleted_rows: List[BlobDeleteResult] = []
    candidate_shas: List[str] = []

    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM projects WHERE id = :pid"), {"pid": project_id}).scalar()
        if not exists:
            raise KeyError("project_not_found")

        snapshot_shas = [
            str(x)
            for x in conn.execute(
                text(
                    """
                    SELECT DISTINCT sf.file_sha256
                    FROM snapshot_files sf
                    JOIN snapshots s ON s.id = sf.snapshot_id
                    WHERE s.project_id = :pid
                    """
                ),
                {"pid": project_id},
            ).scalars().all()
        ]

        thumbnail_shas = [
            str(x)
            for x in conn.execute(
                text(
                    """
                    SELECT DISTINCT thumbnail_blob_sha256
                    FROM portfolio_showcases
                    WHERE project_id = :pid
                      AND thumbnail_blob_sha256 IS NOT NULL
                    """
                ),
                {"pid": project_id},
            ).scalars().all()
        ]

        candidate_shas = list(dict.fromkeys(snapshot_shas + thumbnail_shas))

        conn.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": project_id})

        blob_deleted_rows = _gc_unreferenced_blobs(conn, candidate_shas)
        blob_paths = [r.stored_path for r in blob_deleted_rows]

    fs_deleted = _delete_paths_best_effort(blob_paths)

    return {
        "project_id": project_id,
        "deleted": True,
        "gc": {
            "candidate_shas": int(len(candidate_shas)),
            "blobs_deleted": len(blob_deleted_rows),
            "files_deleted_from_disk": int(fs_deleted),
            "deleted_sha256": [r.deleted_sha256 for r in blob_deleted_rows],
        },
    }
