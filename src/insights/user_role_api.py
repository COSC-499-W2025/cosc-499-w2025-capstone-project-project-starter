"""
FastAPI router for user role management on projects.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .storage import ProjectInsightsStore
from .user_role_store import ProjectRoleStore, load_project_insight_with_role, resolve_db_path

router = APIRouter(prefix="/insights", tags=["insights"])


def get_insights_store(db_url: Optional[str] = None) -> ProjectInsightsStore:
    db_path = resolve_db_path(db_url)
    return ProjectInsightsStore(db_path=db_path)


def get_role_store(db_url: Optional[str] = None) -> ProjectRoleStore:
    db_path = resolve_db_path(db_url)
    return ProjectRoleStore(db_path=db_path)


class UserRolePayload(BaseModel):
    user_role: str = Field(..., description="User's role in the project")


@router.get("/projects/{zip_hash}/{project_name}")
def get_project_with_role(
    zip_hash: str,
    project_name: str,
    store: ProjectInsightsStore = Depends(get_insights_store),
    role_store: ProjectRoleStore = Depends(get_role_store),
):
    payload = load_project_insight_with_role(
        zip_hash,
        project_name,
        store=store,
        role_store=role_store,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="project not found")
    return payload


@router.put("/projects/{zip_hash}/{project_name}/role")
def set_project_role(
    zip_hash: str,
    project_name: str,
    payload: UserRolePayload,
    role_store: ProjectRoleStore = Depends(get_role_store),
):
    ok = role_store.set_user_role(zip_hash, project_name, payload.user_role)
    if not ok:
        raise HTTPException(status_code=404, detail="project not found")
    return {"status": "ok", "zip_hash": zip_hash, "project_name": project_name, "user_role": payload.user_role}
