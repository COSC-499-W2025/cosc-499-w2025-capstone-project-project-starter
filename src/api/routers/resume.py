from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_store
from src.insights.storage import ProjectInsightsStore
from src.project.presentation import generate_items_from_project_id


router = APIRouter(prefix="/resume", tags=["resume"])


class ResumeEditPayload(BaseModel):
    bullets: List[str] = Field(default_factory=list)


@router.get("/{project_id}")
def get_resume(project_id: int, store: ProjectInsightsStore = Depends(get_store)):
    payload = store.load_project_insight_by_id(project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Project not found")
    resume_item = payload.get("resume_item") or {}
    return {"project_id": project_id, "resume_item": resume_item}


@router.post("/generate")
def generate_resume(project_id: int, store: ProjectInsightsStore = Depends(get_store)):
    result = generate_items_from_project_id(project_id, store=store, regenerate=True)
  
    resume = result.get("resume_item") or {}
    bullets = list(resume.get("bullets") or [])
    if bullets:
        store.replace_resume_bullets(project_id, bullets)
    return {"project_id": project_id, "resume_item": resume}


@router.post("/{project_id}/edit")
def edit_resume(
    project_id: int,
    payload: ResumeEditPayload,
    store: ProjectInsightsStore = Depends(get_store),
):
    
    changed = store.replace_resume_bullets(project_id, payload.bullets)
    if not changed:
        raise HTTPException(status_code=404, detail="Project not found")
    updated = store.load_project_insight_by_id(project_id)
    return {"status": "ok", "project_id": project_id, "resume_item": updated.get("resume_item")}
