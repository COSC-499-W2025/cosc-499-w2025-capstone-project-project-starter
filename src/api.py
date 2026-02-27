"""
FastAPI application for Skill Scope milestone API endpoints.

This module keeps the existing scan endpoints while adding project/resume/portfolio
endpoints for milestone requirements.
"""

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_store import (
    create_portfolio_artifact,
    create_resume_artifact,
    get_portfolio_artifact,
    get_privacy_settings,
    get_project_customization,
    get_resume_artifact,
    set_privacy_settings,
    update_portfolio_artifact,
    update_resume_artifact,
    upsert_project_customization,
)
from db import (
    delete_full_scan_by_id,
    get_full_scan_by_id,
    list_full_scans,
    save_full_scan,
    scan_exists,
    update_full_scan,
)

logger = logging.getLogger(__name__)

VALID_ANALYSIS_MODES = {"basic", "advanced"}
VALID_ADVANCED_OPTION_KEYS = {
    "programming_scan",
    "framework_scan",
    "skills_gen",
    "resume_gen",
}


class PrivacyConsentPayload(BaseModel):
    consent: bool
    external_services_allowed: bool = False
    notes: str = ""


class ProjectEditPayload(BaseModel):
    ranking: Optional[int] = None
    chronology_correction: Optional[Dict[str, Any]] = None
    comparison_attributes: Optional[Dict[str, Any]] = None
    highlighted_skills: Optional[List[str]] = None
    selected_for_showcase: Optional[bool] = None
    role: Optional[str] = None
    evidence_of_success: Optional[Any] = None
    thumbnail: Optional[str] = None
    portfolio_showcase_text: Optional[str] = None
    resume_wording: Optional[str] = None


class ResumeGeneratePayload(BaseModel):
    scan_id: Optional[int] = None
    project_ids: List[str] = Field(default_factory=list)
    title: str = "Generated Resume"
    selected_project_ids: List[str] = Field(default_factory=list)
    project_order: List[str] = Field(default_factory=list)


class ResumeEditPayload(BaseModel):
    title: Optional[str] = None
    project_order: Optional[List[str]] = None
    selected_project_ids: Optional[List[str]] = None
    items: Optional[List[Dict[str, Any]]] = None
    project_wording_edits: Optional[Dict[str, str]] = None


class PortfolioGeneratePayload(BaseModel):
    scan_id: Optional[int] = None
    project_ids: List[str] = Field(default_factory=list)
    title: str = "Generated Portfolio"
    selected_project_ids: List[str] = Field(default_factory=list)
    project_order: List[str] = Field(default_factory=list)


class PortfolioEditPayload(BaseModel):
    title: Optional[str] = None
    project_order: Optional[List[str]] = None
    selected_project_ids: Optional[List[str]] = None
    items: Optional[List[Dict[str, Any]]] = None
    project_edits: Optional[Dict[str, ProjectEditPayload]] = None


def _parse_bool(value: Any, default: bool = False) -> bool:
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
    if value is None or value == "":
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


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _model_dump_exclude_none(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _check_file_validity(zip_path: str):
    from file_parser import check_file_validity

    return check_file_validity(zip_path)


def _analyze_scan(file_list: list, analysis_mode: str, advanced_options: Optional[Dict[str, bool]]):
    from services.scan_service import analyze_scan

    return analyze_scan(file_list, analysis_mode, advanced_options)


def _merge_scans(existing_data: Dict[str, Any], new_data: Dict[str, Any]):
    from services.scan_service import merge_scans

    return merge_scans(existing_data, new_data)


def _split_project_id(project_id: str) -> Tuple[int, int]:
    try:
        scan_str, project_idx_str = project_id.split(":", 1)
        return int(scan_str), int(project_idx_str)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="project id must be in '<scan_id>:<index>' format") from exc


def _project_id(scan_id: int, project_index: int) -> str:
    return f"{scan_id}:{project_index}"


def _apply_project_customization(project_record: Dict[str, Any], customization: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = dict(project_record)
    if customization:
        custom = dict(customization)
        custom.pop("updated_at", None)
        merged["customization"] = custom
        for key in (
            "ranking",
            "chronology_correction",
            "comparison_attributes",
            "highlighted_skills",
            "selected_for_showcase",
            "role",
            "evidence_of_success",
            "thumbnail",
            "portfolio_showcase_text",
            "resume_wording",
        ):
            if key in custom:
                merged[key] = custom[key]
    else:
        merged["customization"] = {}
    return merged


def _build_project_record(scan_id: int, project_index: int, project: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "project_id": _project_id(scan_id, project_index),
        "scan_id": scan_id,
        "project_index": project_index,
        "project_name": project.get("project") or project.get("name") or f"Project {project_index + 1}",
        "data": project,
        "skills": project.get("skills", []),
        "frameworks": project.get("frameworks", []),
        "languages": project.get("languages", []),
        "score": project.get("score"),
        "project_type": project.get("project_type"),
    }
    return _apply_project_customization(base, get_project_customization(base["project_id"]))


def _iter_projects(scan_id: Optional[int] = None) -> List[Dict[str, Any]]:
    project_rows: List[Dict[str, Any]] = []
    if scan_id is not None:
        scan = get_full_scan_by_id(scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="scan not found")
        scans = [scan]
    else:
        scan_meta = list_full_scans()
        scans = []
        for meta in scan_meta:
            full = get_full_scan_by_id(meta["summary_id"])
            if full:
                scans.append(full)

    for scan in scans:
        sid = int(scan["summary_id"])
        project_summaries = (scan.get("scan_data") or {}).get("project_summaries", [])
        for idx, project in enumerate(project_summaries):
            if isinstance(project, dict):
                project_rows.append(_build_project_record(sid, idx, project))
    return project_rows


def _get_project_by_id(project_id: str) -> Dict[str, Any]:
    scan_id, idx = _split_project_id(project_id)
    scan = get_full_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found")
    project_summaries = (scan.get("scan_data") or {}).get("project_summaries", [])
    if idx < 0 or idx >= len(project_summaries):
        raise HTTPException(status_code=404, detail="project not found")
    project = project_summaries[idx]
    if not isinstance(project, dict):
        raise HTTPException(status_code=404, detail="project not found")
    return _build_project_record(scan_id, idx, project)


def _project_sort_key(project: Dict[str, Any]) -> Tuple[int, float, str]:
    custom_rank = project.get("ranking")
    if isinstance(custom_rank, int):
        return (0, -float(custom_rank), project["project_id"])
    score = project.get("score") or 0
    return (1, -float(score), project["project_id"])


def _project_to_resume_item(project: Dict[str, Any]) -> Dict[str, Any]:
    custom_text = project.get("resume_wording")
    project_name = project.get("project_name", "Unnamed Project")
    role = project.get("role")
    evidence = project.get("evidence_of_success")
    skills = project.get("highlighted_skills") or project.get("skills") or []

    if custom_text:
        text = custom_text
    else:
        parts = [f"Contributed to {project_name}"]
        if role:
            parts.append(f"as {role}")
        if skills:
            parts.append(f"highlighting {', '.join(map(str, skills[:5]))}")
        if evidence:
            parts.append(f"with evidence of success: {evidence}")
        text = "; ".join(parts) + "."
    return {
        "project_id": project["project_id"],
        "project_name": project_name,
        "text": text,
        "role": role,
        "evidence_of_success": evidence,
    }


def _project_to_portfolio_item(project: Dict[str, Any]) -> Dict[str, Any]:
    project_name = project.get("project_name", "Unnamed Project")
    custom_text = project.get("portfolio_showcase_text")
    role = project.get("role")
    evidence = project.get("evidence_of_success")
    thumbnail = project.get("thumbnail")
    skills = project.get("highlighted_skills") or project.get("skills") or []

    if custom_text:
        text = custom_text
    else:
        text_parts = [f"{project_name} showcase"]
        if role:
            text_parts.append(f"role: {role}")
        if skills:
            text_parts.append(f"skills: {', '.join(map(str, skills[:6]))}")
        if evidence:
            text_parts.append(f"evidence: {evidence}")
        text = " | ".join(text_parts)

    return {
        "project_id": project["project_id"],
        "project_name": project_name,
        "text": text,
        "role": role,
        "evidence_of_success": evidence,
        "thumbnail": thumbnail,
        "comparison_attributes": project.get("comparison_attributes", {}),
    }


def _ordered_project_ids(candidates: List[Dict[str, Any]], explicit_order: Optional[List[str]] = None) -> List[str]:
    ids = [p["project_id"] for p in sorted(candidates, key=_project_sort_key)]
    if not explicit_order:
        return ids
    ordered: List[str] = []
    seen = set()
    for pid in explicit_order:
        if pid in ids and pid not in seen:
            ordered.append(pid)
            seen.add(pid)
    for pid in ids:
        if pid not in seen:
            ordered.append(pid)
    return ordered


async def _parse_upload_inputs(request: Request) -> Dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    payload: Dict[str, Any] = {}
    form = None
    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = dict(form)
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                payload = body
        except Exception:
            payload = {}

    return {
        "payload": payload,
        "form": form,
        "content_type": content_type,
    }


async def _materialize_zip_from_request(parsed_inputs: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    payload = parsed_inputs["payload"]
    form = parsed_inputs["form"]
    temp_zip_path: Optional[str] = None
    zip_path = payload.get("zip_path")

    if form is not None:
        zip_file = form.get("zip")
        if zip_file is not None and hasattr(zip_file, "read"):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            data = await zip_file.read()
            tmp.write(data)
            tmp.close()
            zip_path = tmp.name
            temp_zip_path = tmp.name
            close_fn = getattr(zip_file, "close", None)
            if callable(close_fn):
                maybe_awaitable = close_fn()
                if hasattr(maybe_awaitable, "__await__"):
                    await maybe_awaitable

    return zip_path, temp_zip_path


def _resolve_incremental_target(payload: Dict[str, Any]) -> Optional[int]:
    existing_scan_id = payload.get("existing_scan_id")
    if existing_scan_id is not None and str(existing_scan_id).strip() != "":
        try:
            return int(existing_scan_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="existing_scan_id must be an integer") from exc

    portfolio_id = payload.get("portfolio_id")
    if portfolio_id is not None and str(portfolio_id).strip() != "":
        try:
            portfolio_id_int = int(portfolio_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="portfolio_id must be an integer") from exc
        artifact = get_portfolio_artifact(portfolio_id_int)
        if not artifact:
            raise HTTPException(status_code=404, detail="portfolio not found")
        if artifact.get("scan_summary_id") is None:
            raise HTTPException(status_code=400, detail="portfolio is not linked to a scan")
        return int(artifact["scan_summary_id"])

    resume_id = payload.get("resume_id")
    if resume_id is not None and str(resume_id).strip() != "":
        try:
            resume_id_int = int(resume_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="resume_id must be an integer") from exc
        artifact = get_resume_artifact(resume_id_int)
        if not artifact:
            raise HTTPException(status_code=404, detail="resume not found")
        if artifact.get("scan_summary_id") is None:
            raise HTTPException(status_code=400, detail="resume is not linked to a scan")
        return int(artifact["scan_summary_id"])

    return None


async def _handle_scan_upload(request: Request, include_project_summary: bool) -> JSONResponse:
    parsed = await _parse_upload_inputs(request)
    payload = parsed["payload"]
    zip_path, temp_zip_path = await _materialize_zip_from_request(parsed)

    analysis_mode = _parse_analysis_mode(payload.get("analysis_mode"))
    if not analysis_mode:
        raise HTTPException(status_code=400, detail="analysis_mode must be one of: basic, advanced")

    advanced_options, advanced_options_error = _parse_advanced_options(payload.get("advanced_options"))
    if advanced_options_error:
        raise HTTPException(status_code=400, detail=advanced_options_error)
    if analysis_mode == "basic" and advanced_options:
        raise HTTPException(status_code=400, detail="advanced_options is only supported in advanced mode")

    consent = _parse_bool(payload.get("consent"), default=False)
    persist = _parse_bool(payload.get("persist"), default=True)
    allow_duplicate = _parse_bool(payload.get("allow_duplicate"), default=False)
    incremental = _parse_bool(payload.get("incremental"), default=False)

    if not zip_path:
        raise HTTPException(status_code=400, detail="zip file or zip_path is required")

    try:
        validation_result = _check_file_validity(str(zip_path))
        if not validation_result:
            raise HTTPException(status_code=400, detail="invalid or empty zip file")

        # Backward compatibility if older code returns only file_list.
        if isinstance(validation_result, tuple) and len(validation_result) == 2:
            file_list, zip_hash = validation_result
        else:
            file_list = validation_result
            zip_hash = None

        results = _analyze_scan(file_list, analysis_mode, advanced_options or {})
        if results is None:
            raise HTTPException(status_code=500, detail="scan execution failed")

        if isinstance(results, dict) and zip_hash:
            results["zip_hash"] = zip_hash
            source_hashes = list(results.get("source_hashes", []))
            if zip_hash not in source_hashes:
                source_hashes.append(zip_hash)
            results["source_hashes"] = source_hashes

        persisted_scan_id: Optional[int] = None
        duplicate = False
        merge_applied = False

        target_scan_id = _resolve_incremental_target(payload) if incremental else None

        if persist:
            if zip_hash and not target_scan_id and not allow_duplicate and scan_exists(zip_hash):
                duplicate = True
            elif target_scan_id:
                existing_scan = get_full_scan_by_id(target_scan_id)
                if not existing_scan:
                    raise HTTPException(status_code=404, detail="target scan not found")
                existing_data = (existing_scan.get("scan_data") or {})
                existing_hashes = set(existing_data.get("source_hashes", []))
                if zip_hash and (zip_hash in existing_hashes) and not allow_duplicate:
                    duplicate = True
                    persisted_scan_id = target_scan_id
                else:
                    merged = _merge_scans(existing_data, results)
                    update_full_scan(target_scan_id, merged)
                    persisted_scan_id = target_scan_id
                    merge_applied = True
            else:
                persisted_scan_id = save_full_scan(results, analysis_mode, consent)

        response_body: Dict[str, Any] = {
            "analysis_mode": analysis_mode,
            "persisted": persist,
            "duplicate": duplicate,
            "incremental": incremental,
            "merged": merge_applied,
            "summary_id": persisted_scan_id,
            "results": _json_safe(results),
        }

        if include_project_summary:
            scan_id_for_projects = persisted_scan_id
            projects = []
            for idx, project in enumerate(results.get("project_summaries", []) if isinstance(results, dict) else []):
                if not isinstance(project, dict):
                    continue
                sid = int(scan_id_for_projects) if scan_id_for_projects is not None else -1
                proj = _build_project_record(sid, idx, project)
                if sid == -1:
                    proj["project_id"] = f"temp:{idx}"
                projects.append(_json_safe(proj))
            response_body["projects"] = projects

        status_code = 201
        if duplicate:
            status_code = 200
            response_body["message"] = "duplicate upload recognized; no duplicate persisted"
        elif merge_applied:
            status_code = 200

        return JSONResponse(content=_json_safe(response_body), status_code=status_code)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Scan execution failed")
        raise HTTPException(status_code=500, detail="scan execution failed")
    finally:
        if temp_zip_path:
            try:
                os.remove(temp_zip_path)
            except OSError:
                pass


def _select_projects_for_artifact(
    scan_id: Optional[int],
    project_ids: List[str],
    selected_project_ids: Optional[List[str]],
    project_order: Optional[List[str]],
) -> Tuple[Optional[int], List[Dict[str, Any]], List[str]]:
    candidates = []
    if project_ids:
        candidates = [_get_project_by_id(pid) for pid in project_ids]
    elif scan_id is not None:
        candidates = _iter_projects(scan_id=scan_id)
    else:
        candidates = _iter_projects()

    if selected_project_ids:
        selected_set = set(selected_project_ids)
        candidates = [p for p in candidates if p["project_id"] in selected_set]

    ordered_ids = _ordered_project_ids(candidates, explicit_order=project_order)
    project_map = {p["project_id"]: p for p in candidates}
    ordered_projects = [project_map[pid] for pid in ordered_ids if pid in project_map]
    return scan_id, ordered_projects, ordered_ids


def create_app() -> FastAPI:
    app = FastAPI(
        title="Skill Scope API",
        version="0.2.0",
        description="FastAPI endpoints for project upload, portfolio, and resume workflows.",
    )

    @app.exception_handler(HTTPException)
    def _http_exception_handler(_request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.get("/health")
    def health():
        """
        Simple health check endpoint to verify the API is running.
        """
        return {"status": "ok"}

    # Legacy scan endpoints kept for compatibility
    @app.post("/scans")
    async def create_scan(request: Request):
        """
        Legacy endpoint for creating a scan.
        Wraps the upload logic but returns a simplified response structure if needed.
        """
        return await _handle_scan_upload(request, include_project_summary=False)

    @app.get("/scans")
    def get_scans():
        """
        Retrieves a list of all historical scans (metadata only).
        """
        try:
            scans = list_full_scans()
        except Exception:
            logger.exception("Failed to list scans")
            raise HTTPException(status_code=500, detail="failed to list scans")
        return {"scans": _json_safe(scans)}

    @app.get("/scans/check")
    def check_scan_exists(file_hash: str = Query(..., min_length=1)):
        """
        Checks if a scan with the given file hash already exists.
        """
        return {"exists": scan_exists(file_hash)}

    @app.get("/scans/{summary_id}")
    def get_scan(summary_id: int = Path(..., ge=1)):
        """
        Retrieves the full detailed analysis results for a specific scan ID.
        """
        try:
            scan = get_full_scan_by_id(summary_id)
        except Exception:
            logger.exception("Failed to fetch scan summary_id=%s", summary_id)
            raise HTTPException(status_code=500, detail="failed to retrieve scan")
        if not scan:
            raise HTTPException(status_code=404, detail="scan not found")
        return {"scan": _json_safe(scan)}

    @app.delete("/scans/{summary_id}")
    def delete_scan(summary_id: int = Path(..., ge=1)):
        """
        Permanently deletes a scan and its associated data from the database.
        """
        try:
            deleted = delete_full_scan_by_id(summary_id)
        except Exception:
            logger.exception("Failed to delete scan summary_id=%s", summary_id)
            raise HTTPException(status_code=500, detail="failed to delete scan")
        if not deleted:
            raise HTTPException(status_code=404, detail="scan not found")
        return {"deleted": True, "summary_id": summary_id}

    # Milestone endpoints
    @app.post("/privacy-consent")
    def post_privacy_consent(payload: PrivacyConsentPayload):
        """
        Updates the user's privacy and data processing consent settings.
        """
        saved = set_privacy_settings(_model_dump(payload))
        return {"privacy": _json_safe(saved)}

    @app.get("/privacy-consent")
    def get_privacy():
        """
        Retrieves the current privacy and consent settings.
        """
        return {"privacy": _json_safe(get_privacy_settings())}

    @app.post("/projects/upload")
    async def upload_projects(request: Request):
        """
        Main entry point for scanning. Accepts a ZIP file or path.
        Performs analysis and persists results. Supports incremental updates.
        """
        return await _handle_scan_upload(request, include_project_summary=True)

    @app.get("/projects")
    def list_projects(scan_id: Optional[int] = Query(None, ge=1)):
        """
        Lists all individual projects found across all scans (or filtered by scan_id).
        """
        projects = _iter_projects(scan_id=scan_id)
        return {"projects": _json_safe(sorted(projects, key=_project_sort_key))}

    @app.get("/projects/{project_id:path}")
    def get_project(project_id: str):
        """
        Retrieves details for a specific project, including any user customizations.
        """
        return {"project": _json_safe(_get_project_by_id(project_id))}

    @app.post("/projects/{project_id:path}/edit")
    def edit_project(project_id: str, payload: ProjectEditPayload):
        """
        Updates project metadata (e.g., custom descriptions, showcase flags).
        """
        _get_project_by_id(project_id)  # validate existence
        saved = upsert_project_customization(project_id, _model_dump_exclude_none(payload))
        return {"project_id": project_id, "customization": _json_safe(saved)}

    @app.get("/skills")
    def get_skills(scan_id: Optional[int] = Query(None, ge=1)):
        """
        Returns an aggregated list of skills and their frequency across projects.
        """
        projects = _iter_projects(scan_id=scan_id)
        skills_count: Dict[str, int] = {}
        for project in projects:
            skills = project.get("highlighted_skills") or project.get("skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            for skill in skills:
                skills_count[str(skill)] = skills_count.get(str(skill), 0) + 1
        skills = [{"skill": name, "project_count": count} for name, count in sorted(skills_count.items())]
        return {"skills": skills}

    @app.post("/resume/generate")
    def generate_resume(payload: ResumeGeneratePayload):
        """
        Creates a new Resume artifact (JSON) based on selected projects.
        """
        scan_id, selected_projects, ordered_ids = _select_projects_for_artifact(
            payload.scan_id,
            payload.project_ids,
            payload.selected_project_ids or None,
            payload.project_order or None,
        )
        items = [_project_to_resume_item(p) for p in selected_projects]
        artifact_data = {
            "kind": "resume",
            "items": items,
            "selected_project_ids": [p["project_id"] for p in selected_projects],
            "project_order": ordered_ids,
        }
        saved = create_resume_artifact(artifact_data, scan_summary_id=scan_id, title=payload.title)
        return {"resume": _json_safe(saved)}

    @app.get("/resume/{resume_id}")
    def get_resume(resume_id: int = Path(..., ge=1)):
        """
        Retrieves a stored Resume artifact.
        """
        artifact = get_resume_artifact(resume_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="resume not found")
        return {"resume": _json_safe(artifact)}

    @app.post("/resume/{resume_id}/edit")
    def edit_resume(resume_id: int, payload: ResumeEditPayload):
        """
        Updates an existing Resume artifact (reorder projects, edit wording).
        """
        artifact = get_resume_artifact(resume_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="resume not found")

        if payload.project_wording_edits:
            for project_id, wording in payload.project_wording_edits.items():
                _get_project_by_id(project_id)  # validate
                upsert_project_customization(project_id, {"resume_wording": wording})

        patch: Dict[str, Any] = _model_dump_exclude_none(payload)
        if payload.selected_project_ids is not None or payload.project_order is not None:
            selected_ids = payload.selected_project_ids or artifact["data"].get("selected_project_ids", [])
            ordered_ids = payload.project_order or artifact["data"].get("project_order", [])
            selected_projects = [_get_project_by_id(pid) for pid in selected_ids]
            ordered_ids = _ordered_project_ids(selected_projects, explicit_order=ordered_ids)
            project_map = {p["project_id"]: p for p in selected_projects}
            patch["items"] = [_project_to_resume_item(project_map[pid]) for pid in ordered_ids if pid in project_map]
            patch["selected_project_ids"] = selected_ids
            patch["project_order"] = ordered_ids

        saved = update_resume_artifact(resume_id, patch)
        return {"resume": _json_safe(saved)}

    @app.post("/portfolio/generate")
    def generate_portfolio(payload: PortfolioGeneratePayload):
        """
        Creates a new Portfolio artifact (JSON). Honors 'selected_for_showcase' flags.
        """
        scan_id, selected_projects, ordered_ids = _select_projects_for_artifact(
            payload.scan_id,
            payload.project_ids,
            payload.selected_project_ids or None,
            payload.project_order or None,
        )
        # Default showcase selection honors project customization if explicit selection not provided.
        if not payload.selected_project_ids:
            showcase_filtered = [
                p for p in selected_projects if p.get("selected_for_showcase") is not False
            ]
            if showcase_filtered:
                selected_projects = showcase_filtered
        items = [_project_to_portfolio_item(p) for p in selected_projects]
        artifact_data = {
            "kind": "portfolio",
            "items": items,
            "selected_project_ids": [p["project_id"] for p in selected_projects],
            "project_order": ordered_ids,
        }
        saved = create_portfolio_artifact(artifact_data, scan_summary_id=scan_id, title=payload.title)
        return {"portfolio": _json_safe(saved)}

    @app.get("/portfolio/{portfolio_id}")
    def get_portfolio(portfolio_id: int = Path(..., ge=1)):
        """
        Retrieves a stored Portfolio artifact.
        """
        artifact = get_portfolio_artifact(portfolio_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="portfolio not found")
        return {"portfolio": _json_safe(artifact)}

    @app.post("/portfolio/{portfolio_id}/edit")
    def edit_portfolio(portfolio_id: int, payload: PortfolioEditPayload):
        """
        Updates an existing Portfolio artifact.
        """
        artifact = get_portfolio_artifact(portfolio_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="portfolio not found")

        if payload.project_edits:
            for project_id, edit in payload.project_edits.items():
                _get_project_by_id(project_id)  # validate
                upsert_project_customization(project_id, _model_dump_exclude_none(edit))

        patch: Dict[str, Any] = _model_dump_exclude_none(payload)
        if payload.selected_project_ids is not None or payload.project_order is not None:
            selected_ids = payload.selected_project_ids or artifact["data"].get("selected_project_ids", [])
            ordered_ids = payload.project_order or artifact["data"].get("project_order", [])
            selected_projects = [_get_project_by_id(pid) for pid in selected_ids]
            ordered_ids = _ordered_project_ids(selected_projects, explicit_order=ordered_ids)
            project_map = {p["project_id"]: p for p in selected_projects}
            patch["items"] = [_project_to_portfolio_item(project_map[pid]) for pid in ordered_ids if pid in project_map]
            patch["selected_project_ids"] = selected_ids
            patch["project_order"] = ordered_ids

        saved = update_portfolio_artifact(portfolio_id, patch)
        return {"portfolio": _json_safe(saved)}

    return app


app = create_app()


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:  # pragma: no cover
        raise SystemExit("Install uvicorn to run the FastAPI app directly")

    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=True)
