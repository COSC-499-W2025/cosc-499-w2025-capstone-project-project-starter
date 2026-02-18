"""
Flask API skeleton for Skill Scope.
"""

import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from flask import Flask, jsonify, request

from db import delete_full_scan_by_id, get_full_scan_by_id, list_full_scans
from file_parser import check_file_validity
from services.scan_service import run_scan

logger = logging.getLogger(__name__)

VALID_ANALYSIS_MODES = {"basic", "advanced"}
VALID_ADVANCED_OPTION_KEYS = {
    "programming_scan",
    "framework_scan",
    "skills_gen",
    "resume_gen",
}


def _parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return default


def _parse_analysis_mode(value: Any) -> Optional[str]:
    if value is None:
        return "basic"
    if not isinstance(value, str):
        return None
    parsed = value.strip().lower()
    if not parsed:
        return "basic"
    if parsed not in VALID_ANALYSIS_MODES:
        return None
    return parsed


def _parse_advanced_options(value: Any) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
    if value is None:
        return {}, None
    if isinstance(value, dict):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None, "advanced_options must be valid JSON"
        if not isinstance(parsed, dict):
            return None, "advanced_options must be a JSON object"
    else:
        return None, "advanced_options must be an object"

    normalized: Dict[str, bool] = {}
    for key, option_value in parsed.items():
        if key not in VALID_ADVANCED_OPTION_KEYS:
            return None, f"unsupported advanced option: {key}"
        if not isinstance(option_value, bool):
            return None, f"advanced option '{key}' must be boolean"
        normalized[key] = option_value

    return normalized, None


def _json_safe(payload: Any) -> Any:
    return json.loads(json.dumps(payload, default=str))


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/scans")
    def create_scan():
        payload = request.get_json(silent=True) or {}
        analysis_mode = _parse_analysis_mode(
            request.form.get("analysis_mode")
            or payload.get("analysis_mode")
        )
        if not analysis_mode:
            return jsonify({"error": "analysis_mode must be one of: basic, advanced"}), 400
        consent = _parse_bool(
            request.form.get("consent") or payload.get("consent"),
            default=False,
        )
        persist = _parse_bool(
            request.form.get("persist") or payload.get("persist"),
            default=True,
        )
        advanced_options, advanced_options_error = _parse_advanced_options(
            request.form.get("advanced_options") or payload.get("advanced_options")
        )
        if advanced_options_error:
            return jsonify({"error": advanced_options_error}), 400
        if analysis_mode == "basic" and advanced_options:
            return jsonify({"error": "advanced_options is only supported in advanced mode"}), 400

        zip_file = request.files.get("zip")
        zip_path = payload.get("zip_path")
        temp_zip_path = None

        if zip_file:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            zip_file.save(tmp.name)
            tmp.close()
            zip_path = tmp.name
            temp_zip_path = tmp.name

        if not zip_path:
            return jsonify({"error": "zip file or zip_path is required"}), 400

        try:
            file_list = check_file_validity(zip_path)
            if not file_list:
                return jsonify({"error": "invalid or empty zip file"}), 400

            results = run_scan(
                file_list,
                analysis_mode,
                advanced_options,
                consent=consent,
                persist=persist,
            )
        except Exception:
            logger.exception(
                "Scan execution failed: analysis_mode=%s persist=%s",
                analysis_mode,
                persist,
            )
            return jsonify({"error": "scan execution failed"}), 500
        finally:
            if temp_zip_path:
                try:
                    os.remove(temp_zip_path)
                except OSError:
                    pass

        return (
            jsonify(
                {
                    "analysis_mode": analysis_mode,
                    "persisted": persist,
                    "results": _json_safe(results),
                }
            ),
            201,
        )

    @app.get("/scans")
    def get_scans():
        try:
            scans = list_full_scans()
        except Exception:
            logger.exception("Failed to list scans")
            return jsonify({"error": "failed to list scans"}), 500
        return jsonify({"scans": _json_safe(scans)})

    @app.get("/scans/<int:summary_id>")
    def get_scan(summary_id: int):
        try:
            scan = get_full_scan_by_id(summary_id)
        except Exception:
            logger.exception("Failed to fetch scan summary_id=%s", summary_id)
            return jsonify({"error": "failed to retrieve scan"}), 500
        if not scan:
            return jsonify({"error": "scan not found"}), 404
        return jsonify({"scan": _json_safe(scan)})

    @app.delete("/scans/<int:summary_id>")
    def delete_scan(summary_id: int):
        try:
            deleted = delete_full_scan_by_id(summary_id)
        except Exception:
            logger.exception("Failed to delete scan summary_id=%s", summary_id)
            return jsonify({"error": "failed to delete scan"}), 500
        if not deleted:
            return jsonify({"error": "scan not found"}), 404
        return jsonify({"deleted": True, "summary_id": summary_id})

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
