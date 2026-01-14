from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import text
from src.db.session import get_engine
from src.worker.executors import run_parser, run_git_metrics, run_local_ml

POLL_INTERVAL_SECS = float(os.environ.get("WORKER_POLL_INTERVAL_SECS", "2.0"))
BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "5"))


def _claim_one_pending(engine) -> Optional[Dict[str, Any]]:
    """
    Claim one pending analysis row using FOR UPDATE SKIP LOCKED so multiple workers can run safely.
    Returns mapping with keys: id, snapshot_id, analysis_type.
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                WITH next_job AS (
                  SELECT id, snapshot_id, analysis_type
                  FROM analyses
                  WHERE status = 'pending'
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE analyses a
                SET status = 'running',
                    started_at = NOW()
                FROM next_job
                WHERE a.id = next_job.id
                RETURNING a.id, a.snapshot_id, a.analysis_type
                """
            )
        ).mappings().first()

        return {
            "id": str(row["id"]),
            "snapshot_id": str(row["snapshot_id"]),
            "analysis_type": row["analysis_type"],
        } if row else None



def _finish(engine, analysis_id: str, *, status: str, output: Dict[str, Any]) -> None:
    payload = json.dumps(output, default=str)  # handles UUID, Path, etc.

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE analyses
                SET status = :status,
                    completed_at = NOW(),
                    output_json = CAST(:out AS jsonb)
                WHERE id = :id
                """
            ),
            {"status": status, "out": payload, "id": str(analysis_id)},
        )


def _fail(engine, analysis_id: str, err: str) -> None:
    _finish(engine, analysis_id, status="failed", output={"error": err})


def main():
    engine = get_engine()
    while True:
        job = _claim_one_pending(engine)
        if not job:
            time.sleep(POLL_INTERVAL_SECS)
            continue

        analysis_id = job["id"]
        snapshot_id = job["snapshot_id"]
        analysis_type = job["analysis_type"]

        try:
            if analysis_type == "parser":
                out = run_parser(engine, snapshot_id)
                _finish(engine, analysis_id, status="complete", output=out)
            elif analysis_type == "git_metrics":
                out = run_git_metrics(engine, snapshot_id)
                _finish(engine, analysis_id, status="complete", output=out)
            elif analysis_type == "local_ml":
                out = run_local_ml(engine, analysis_id, snapshot_id)
                _finish(engine, analysis_id, status="complete", output=out)
            else:
                _fail(engine, analysis_id, f"unknown analysis_type: {analysis_type}")
        except Exception as e:
            _fail(engine, analysis_id, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
