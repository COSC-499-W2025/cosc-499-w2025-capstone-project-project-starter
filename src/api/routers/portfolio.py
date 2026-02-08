from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_role_store, get_store
from src.insights.storage import ProjectInsightsStore
from src.insights.user_role_store import ProjectRoleStore
from src.pipeline.presentation_pipeline import PresentationPipeline

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _build_key_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_files": metrics.get("total_files", 0),
        "total_lines": metrics.get("total_lines", 0),
        "total_commits": metrics.get("total_commits", 0),
        "total_contributors": metrics.get("total_contributors", 0),
        "doc_files": metrics.get("doc_files", 0),
        "image_files": metrics.get("image_files", 0),
        "video_files": metrics.get("video_files", 0),
        "test_files": metrics.get("test_files", 0),
    }


@router.get("/{project_id}")
def get_portfolio_showcase(
    project_id: int,
    store: ProjectInsightsStore = Depends(get_store),
    role_store: ProjectRoleStore = Depends(get_role_store),
):
    payload = store.load_project_insight_by_id(project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = PresentationPipeline(insights_store=store)._get_project_metadata(project_id)
    user_role: Optional[str] = None
    if metadata:
        user_role = role_store.get_user_role(metadata["zip_hash"], metadata["project_name"])

    project_name = payload.get("project_name")
    portfolio_item = payload.get("portfolio_item") or {}
    project_metrics = payload.get("project_metrics") or {}
    key_skills = portfolio_item.get("skills") or project_metrics.get("skills") or []

    response: Dict[str, Any] = {
        "project_id": project_id,
        "project_title": project_name,
        "user_role": user_role,
        "description": portfolio_item.get("description"),
        "summary": portfolio_item.get("summary") or portfolio_item.get("description"),
        "key_skills": key_skills,
        "key_metrics": _build_key_metrics(project_metrics),
    }

    success_metrics = payload.get("success_metrics")
    if success_metrics and "error" not in success_metrics:
        response["success_metrics"] = success_metrics

    return response


class PortfolioEditPayload(BaseModel):
    tagline: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    complexity: Optional[str] = None
    is_collaborative: Optional[bool] = None
    summary: Optional[str] = None
    key_features: Optional[List[str]] = Field(default=None)


@router.post("/{project_id}/edit")
def edit_portfolio(
    project_id: int,
    payload: PortfolioEditPayload,
    store: ProjectInsightsStore = Depends(get_store),
):
    fields: Dict[str, Any] = {}
    for k in ("tagline", "description", "project_type", "complexity", "is_collaborative", "summary", "key_features"):
        v = getattr(payload, k)
        if v is not None:
            fields[k] = v
    changed = store.update_portfolio_insights_fields(project_id, fields)
    if not changed:
        raise HTTPException(status_code=404, detail="Project not found or no changes")
    updated = store.load_project_insight_by_id(project_id)
    return {"status": "ok", "project_id": project_id, "portfolio_item": updated.get("portfolio_item")}


@router.post("/generate")
def generate_portfolio(project_id: int, store: ProjectInsightsStore = Depends(get_store)):
   
    from src.project.presentation import generate_items_from_project_id

    result = generate_items_from_project_id(project_id, store=store, regenerate=True)
    portfolio = result.get("portfolio_item") or {}
    persist_fields = {
        k: portfolio.get(k)
        for k in ("tagline", "description", "project_type", "complexity", "is_collaborative", "summary", "key_features")
        if k in portfolio
    }
    if persist_fields:
        store.update_portfolio_insights_fields(project_id, persist_fields)
    return {"project_id": project_id, "portfolio_item": portfolio}
