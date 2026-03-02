from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import text
from src.db.session import get_engine
from src.worker.executors import run_parser, run_git_metrics, run_local_ml, run_external_llm

POLL_INTERVAL_SECS = float(os.environ.get("WORKER_POLL_INTERVAL_SECS", "2.0"))
BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "5"))


def _configure_logging() -> None:
    level_name = str(os.getenv("ARTIFACT_MINER_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(level)


_configure_logging()
logger = logging.getLogger(__name__)


def _claim_one_pending(engine) -> Optional[Dict[str, Any]]:
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

        return (
            {"id": str(row["id"]), "snapshot_id": str(row["snapshot_id"]), "analysis_type": row["analysis_type"]}
            if row
            else None
        )


def _finish(engine, analysis_id: str, *, status: str, output: Dict[str, Any]) -> None:
    payload = json.dumps(output, default=str)

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


def _queue_local_ml_if_missing(engine, snapshot_id: str) -> None:
    with engine.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT id
                FROM analyses
                WHERE snapshot_id = :sid AND analysis_type = 'local_ml'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"sid": str(snapshot_id)},
        ).scalar()

        if existing:
            return

        conn.execute(
            text(
                """
                INSERT INTO analyses (snapshot_id, analysis_type, status)
                VALUES (:sid, 'local_ml', 'pending')
                """
            ),
            {"sid": str(snapshot_id)},
        )
        logger.debug("Queued local_ml fallback analysis for snapshot %s", snapshot_id)


def main():
    engine = get_engine()
    logger.info("Worker poller started (poll_interval_secs=%s)", POLL_INTERVAL_SECS)
    while True:
        job = _claim_one_pending(engine)
        if not job:
            time.sleep(POLL_INTERVAL_SECS)
            continue

        analysis_id = job["id"]
        snapshot_id = job["snapshot_id"]
        analysis_type = job["analysis_type"]
        logger.debug(
            "Claimed analysis job id=%s type=%s snapshot_id=%s",
            analysis_id,
            analysis_type,
            snapshot_id,
        )

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
            elif analysis_type == "external_llm":
                out = run_external_llm(engine, analysis_id, snapshot_id)
                _finish(engine, analysis_id, status="complete", output=out)
            else:
                logger.warning("Unknown analysis type '%s' for analysis_id=%s", analysis_type, analysis_id)
                _fail(engine, analysis_id, f"unknown analysis_type: {analysis_type}")
                continue
            logger.debug("Completed analysis job id=%s type=%s", analysis_id, analysis_type)
        except Exception as e:
            if analysis_type == "external_llm":
                _queue_local_ml_if_missing(engine, snapshot_id)
                logger.warning(
                    "External analysis failed; local_ml fallback queued for snapshot %s",
                    snapshot_id,
                )
            logger.exception("Analysis job failed id=%s type=%s", analysis_id, analysis_type)
            _fail(engine, analysis_id, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
