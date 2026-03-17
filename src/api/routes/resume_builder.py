"""Resume builder API: multiple named resumes, sidebar, edit, export PDF/HTML/Markdown."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from resume.resume_builder_service import (
    ResumeNotFoundError,
    ResumePersistenceError,
    add_projects_to_resume,
    attach_projects_to_resume,
    build_resume_model,
    create_resume,
    delete_resume,
    list_resumes,
    load_saved_resume,
    remove_project_from_resume,
    resume_exists,
    save_resume_edits,
)
from resume.resume_export import export_markdown, export_pdf, render_html

router = APIRouter()


class ResumeFilter(BaseModel):
    name: str = Field(..., min_length=1)
    project_ids: List[int] = Field(..., min_length=1)


class AddProjectsBody(BaseModel):
    project_ids: List[int] = Field(..., description="List of project IDs to add")


def _get_resume_model(
    user_name: str,
    project_ids: Optional[List[int]] = None,
    resume_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Return the resume model dict for the given user/filter."""
    if resume_id is not None:
        if resume_id == 0:
            return build_resume_model(user_name, project_ids=None)
        return load_saved_resume(user_name, resume_id)
    return build_resume_model(user_name, project_ids=project_ids)


@router.get("/resume")
def get_resume(
    user_name: str = Query(..., description="Current user"),
    project_ids: Optional[List[int]] = Query(None, description="Filter by project IDs for preview"),
):
    """GET preview: no project_ids = master resume; with project_ids = filtered preview."""
    try:
        model = build_resume_model(user_name, project_ids=project_ids)
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume/{resume_id}")
def get_saved_resume(
    resume_id: int,
    user_name: str = Query(...),
):
    """Load saved resume by id. resume_id=1 returns master."""
    try:
        if resume_id == 0:
            return build_resume_model(user_name, project_ids=None)
        return load_saved_resume(user_name, resume_id)
    except ResumeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume_names")
def list_resumes_endpoint(user_name: str = Query(...)):
    """List resumes for sidebar: id, name, is_master."""
    try:
        return {"resumes": list_resumes(user_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
def create_tailored_resume(
    filter_body: ResumeFilter,
    user_name: str = Query(...),
):
    """Create a new resume with selected projects."""
    try:
        resume_id = create_resume(user_name, filter_body.name)
        attach_projects_to_resume(user_name, resume_id, filter_body.project_ids)
        return {"resume_id": resume_id, "message": "Resume created successfully"}
    except ResumePersistenceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/{resume_id}/edit")
def save_edited_resume(
    resume_id: int,
    payload: Dict[str, Any],
    user_name: str = Query(...),
):
    """Save edits (skills, projects with overrides)."""
    try:
        if not resume_exists(user_name, resume_id):
            raise HTTPException(status_code=404, detail="Resume not found")
        save_resume_edits(user_name, resume_id, payload)
        return {"status": "ok", "message": "Resume edits saved"}
    except ResumeNotFoundError:
        raise HTTPException(status_code=404, detail="Resume not found")
    except ResumePersistenceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/export")
async def export_resume(
    payload: Dict[str, Any] = Body(...),
    format: str = Query("pdf", description="Export format: pdf, html, or markdown"),
    user_name: str = Query(..., description="Current user (for logging)"),
):
    """Export resume from request body (FullResumeData or legacy shape). No persistence."""
    fmt = (format or "pdf").lower().strip()
    if fmt not in ("pdf", "html", "markdown"):
        raise HTTPException(400, "format must be pdf, html, or markdown")
    try:
        if fmt == "pdf":
            pdf_bytes = await run_in_threadpool(export_pdf, payload)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
            )
        if fmt == "html":
            html_str = render_html(payload)
            return Response(
                content=html_str,
                media_type="text/html",
                headers={"Content-Disposition": 'attachment; filename="resume.html"'},
            )
        md_str = export_markdown(payload)
        return Response(
            content=md_str,
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="resume.md"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume/export/pdf")
async def export_pdf_get(
    user_name: str = Query(...),
    project_ids: Optional[List[int]] = Query(None),
    resume_id: Optional[int] = Query(None),
):
    """Export resume as PDF by user/resume_id (loads from DB)."""
    if project_ids and resume_id is not None:
        raise HTTPException(400, "Cannot specify both project_ids and resume_id.")
    try:
        model = _get_resume_model(user_name, project_ids=project_ids, resume_id=resume_id)
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    pdf_bytes = await run_in_threadpool(export_pdf, model)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
    )


@router.post("/resume/{resume_id}/projects")
def add_projects_endpoint(
    resume_id: int,
    body: AddProjectsBody,
    user_name: str = Query(...),
):
    """Add projects to an existing resume."""
    if resume_id == 0:
        raise HTTPException(400, "Cannot add projects to Master Resume.")
    try:
        add_projects_to_resume(user_name, resume_id, body.project_ids)
        return {"success": True, "message": f"Projects added to resume {resume_id}", "resume_id": resume_id}
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except ResumePersistenceError as e:
        raise HTTPException(409, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.delete("/resume/{resume_id}/project/{project_id}")
def delete_project_from_resume_endpoint(
    resume_id: int,
    project_id: int,
    user_name: str = Query(...),
):
    """Remove a project from a resume."""
    try:
        remove_project_from_resume(user_name, resume_id, project_id)
        return {"success": True, "message": f"Project {project_id} removed", "resume_id": resume_id, "project_id": project_id}
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.delete("/resume/{resume_id}")
def delete_resume_endpoint(
    resume_id: int,
    user_name: str = Query(...),
):
    """Delete a saved resume (not master)."""
    if resume_id == 0:
        raise HTTPException(400, "Cannot delete Master Resume.")
    try:
        delete_resume(user_name, resume_id)
        return {"success": True, "message": f"Resume {resume_id} deleted", "deleted_resume_id": resume_id}
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except ResumePersistenceError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
