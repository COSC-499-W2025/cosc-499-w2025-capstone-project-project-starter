"""Resume builder API (team-3 style): multiple named resumes, sidebar, edit, export PDF/TeX."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
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
from resume.generate_resume_tex import generate_resume_tex

router = APIRouter()

PDF_CACHE_DIR = "/tmp/resume_pdf_cache"
LATEX_BUILD_DIR = "/tmp/latex_build"
os.makedirs(PDF_CACHE_DIR, exist_ok=True)
os.makedirs(LATEX_BUILD_DIR, exist_ok=True)


class ResumeFilter(BaseModel):
    name: str = Field(..., min_length=1)
    project_ids: List[int] = Field(..., min_length=1)


class AddProjectsBody(BaseModel):
    project_ids: List[int] = Field(..., description="List of project IDs to add")


def _tex_hash(tex: str) -> str:
    return hashlib.sha256(tex.encode("utf-8")).hexdigest()


def _get_resume_tex(user_name: str, project_ids: Optional[List[int]] = None, resume_id: Optional[int] = None) -> str:
    if resume_id is not None:
        if resume_id == 0:
            resume_model = build_resume_model(user_name, project_ids=None)
        else:
            resume_model = load_saved_resume(user_name, resume_id)
    else:
        resume_model = build_resume_model(user_name, project_ids=project_ids)
    return generate_resume_tex(resume_model)


def _compile_pdf(tex: str) -> bytes:
    build_id = uuid.uuid4().hex
    build_dir = os.path.join(LATEX_BUILD_DIR, build_id)
    os.makedirs(build_dir, exist_ok=True)
    tex_path = os.path.join(build_dir, "resume.tex")
    pdf_path = os.path.join(build_dir, "resume.pdf")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        if proc.returncode != 0 and not os.path.exists(pdf_path):
            raise subprocess.CalledProcessError(
                proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr
            )
        with open(pdf_path, "rb") as f:
            return f.read()
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "LaTeX compilation timed out.")
    except FileNotFoundError:
        raise HTTPException(500, "pdflatex not found. Install LaTeX.")
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            422,
            {
                "error": "LaTeX compilation failed",
                "stdout": (e.output or b"").decode(errors="ignore")[-1500:],
                "stderr": (e.stderr or b"").decode(errors="ignore")[-1500:],
            },
        )
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def _get_or_compile_pdf(tex: str) -> bytes:
    h = _tex_hash(tex)
    pdf_path = os.path.join(PDF_CACHE_DIR, f"{h}.pdf")
    if os.path.exists(pdf_path) and not os.path.islink(pdf_path):
        with open(pdf_path, "rb") as f:
            return f.read()
    pdf_bytes = _compile_pdf(tex)
    tmp_path = pdf_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)
    if os.path.islink(pdf_path):
        try:
            os.unlink(pdf_path)
        except OSError:
            pass
    os.replace(tmp_path, pdf_path)
    return pdf_bytes


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


@router.get("/resume/export/tex")
def export_tex(
    user_name: str = Query(...),
    project_ids: Optional[List[int]] = Query(None),
    resume_id: Optional[int] = Query(None),
):
    """Export resume as .tex file."""
    if project_ids and resume_id is not None:
        raise HTTPException(400, "Cannot specify both project_ids and resume_id.")
    try:
        tex = _get_resume_tex(user_name, project_ids=project_ids, resume_id=resume_id)
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return Response(
        content=tex,
        media_type="application/x-tex",
        headers={"Content-Disposition": "attachment; filename=resume.tex"},
    )


@router.get("/resume/export/pdf")
async def export_pdf(
    user_name: str = Query(...),
    project_ids: Optional[List[int]] = Query(None),
    resume_id: Optional[int] = Query(None),
):
    """Export resume as PDF."""
    if project_ids and resume_id is not None:
        raise HTTPException(400, "Cannot specify both project_ids and resume_id.")
    try:
        tex = _get_resume_tex(user_name, project_ids=project_ids, resume_id=resume_id)
    except ResumeNotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    pdf_bytes = await run_in_threadpool(_get_or_compile_pdf, tex)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},
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
