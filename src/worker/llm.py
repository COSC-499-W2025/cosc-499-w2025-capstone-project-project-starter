from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

# In pytest, do not invoke any external binaries.
IS_TESTING = "PYTEST_CURRENT_TEST" in os.environ


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExternalLLMConfig:
    """
    External LLM is executed via Ollama CLI (free/local). This avoids requiring an HTTP server.
    Configuration is controlled via env vars for predictability in CI.
    """
    model: str = os.environ.get("OLLAMA_MODEL", "mistral")
    timeout_secs: int = int(os.environ.get("OLLAMA_TIMEOUT_SECS", "120"))
    max_prompt_chars: int = int(os.environ.get("OLLAMA_MAX_PROMPT_CHARS", "24000"))


def ollama_available() -> bool:
    if IS_TESTING:
        return True
    try:
        r = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _trim(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + "\n[TRUNCATED]\n"


def _fetch_latest_completed_output(conn, snapshot_id: str, analysis_type: str) -> Dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT output_json
            FROM analyses
            WHERE snapshot_id = :sid AND analysis_type = :atype AND status = 'complete'
            ORDER BY completed_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """
        ),
        {"sid": snapshot_id, "atype": analysis_type},
    ).mappings().first()
    if not row:
        return {}
    out = row.get("output_json") or {}
    if isinstance(out, dict):
        return out
    return {}


def build_external_prompt(engine: Engine, snapshot_id: str) -> str:
    """
    Builds a prompt that uses already-derived signals (parser/git/local_ml outputs),
    rather than sending raw code blobs. This is smaller, faster, and reduces exposure.
    """
    with engine.connect() as conn:
        parser_out = _fetch_latest_completed_output(conn, snapshot_id, "parser")
        git_out = _fetch_latest_completed_output(conn, snapshot_id, "git_metrics")
        ml_out = _fetch_latest_completed_output(conn, snapshot_id, "local_ml")

    top_skills = []
    skills = ml_out.get("skills", [])
    if isinstance(skills, list):
        for row in skills[:25]:
            if not isinstance(row, dict):
                continue
            top_skills.append(
                {
                    "skill": row.get("skill"),
                    "max_prob": row.get("max_prob"),
                    "hits": row.get("hits"),
                }
            )

    summary_payload = {
        "snapshot_id": snapshot_id,
        "parser": {
            "totals": (parser_out.get("totals") or {}),
            "top_languages": (parser_out.get("top_languages") or [])[:10],
            "activity_counts": (parser_out.get("activity_counts") or {}),
        },
        "git_metrics": {
            "git_repos_found": git_out.get("git_repos_found"),
            "repo_summaries": (git_out.get("repo_summaries") or [])[:5],
            "commit_contributions": (git_out.get("commit_contributions") or {}),
        },
        "local_ml": {
            "threshold": ml_out.get("threshold"),
            "totals": (ml_out.get("totals") or {}),
            "top_skills": top_skills,
        },
    }

    instructions = (
        "You are generating an 'external analysis' summary of a software project snapshot.\n"
        "Use only the provided JSON signals; do not hallucinate files, frameworks, or metrics.\n"
        "Return STRICT JSON with keys:\n"
        "  overview (string <= 120 words),\n"
        "  strengths (array of 3-6 strings),\n"
        "  risks (array of 2-6 strings),\n"
        "  resume_bullets (array of exactly 3 strings),\n"
        "  confidence (number 0..1).\n"
    )

    return instructions + "\nSIGNALS_JSON:\n" + json.dumps(summary_payload, ensure_ascii=False)


def run_ollama(prompt: str, cfg: Optional[ExternalLLMConfig] = None) -> str:
    cfg = cfg or ExternalLLMConfig()

    if IS_TESTING:
        # Deterministic output for tests.
        return json.dumps(
            {
                "overview": "Test external overview.",
                "strengths": ["A", "B", "C"],
                "risks": ["R1", "R2"],
                "resume_bullets": ["B1", "B2", "B3"],
                "confidence": 0.5,
            }
        )

    if not ollama_available():
        raise RuntimeError("ollama is not available (missing binary or not executable)")

    trimmed = _trim(prompt, cfg.max_prompt_chars)

    r = subprocess.run(
        ["ollama", "run", cfg.model],
        input=trimmed,
        capture_output=True,
        text=True,
        timeout=cfg.timeout_secs,
    )
    if r.returncode != 0:
        err = (r.stderr or "").strip()
        raise RuntimeError(f"ollama failed: {err or 'unknown error'}")

    return (r.stdout or "").strip()


def run_external_llm_analysis(engine: Engine, snapshot_id: str) -> Dict[str, Any]:
    """
    Executes the external analysis via Ollama and returns a structured JSON payload.
    """
    prompt = build_external_prompt(engine, snapshot_id)
    raw = run_ollama(prompt)

    # Best effort: parse JSON; if model returns non-JSON, store raw output.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {
                "snapshot_id": snapshot_id,
                "generated_at": _utcnow_iso(),
                "provider": "ollama",
                "model": ExternalLLMConfig().model,
                "result": parsed,
            }
    except Exception:
        pass

    return {
        "snapshot_id": snapshot_id,
        "generated_at": _utcnow_iso(),
        "provider": "ollama",
        "model": ExternalLLMConfig().model,
        "result": None,
        "raw_text": raw,
        "warning": "External model did not return valid JSON.",
    }
