from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_config_manager, get_role_store, get_store
from src.config.config_manager import UserConfigManager
from src.insights.storage import ProjectInsightsStore
from src.insights.user_role_store import ProjectRoleStore
from src.pipeline.presentation_pipeline import PresentationPipeline

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectUploadRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    zip_path: str = Field(..., min_length=1)


class ProjectListItem(BaseModel):
    project_id: int
    project_name: str
    zip_hash: str
    is_git_repo: bool
    code_files: int
    doc_files: int
    created_at: str
    updated_at: str


def _resolve_zip_hash(store: ProjectInsightsStore, zip_path: str) -> Optional[str]:
    runs = store.list_recent_zipfiles(limit=5)
    for run in runs:
        if run.get("zip_path") == zip_path:
            return run.get("zip_hash")
    return runs[0]["zip_hash"] if runs else None


@router.post("/upload")
def upload_projects(
    payload: ProjectUploadRequest,
    store: ProjectInsightsStore = Depends(get_store),
    manager: UserConfigManager = Depends(get_config_manager),
):
    user_id = payload.user_id.strip()
    zip_path = payload.zip_path.strip()
    if not user_id or not zip_path:
        raise HTTPException(status_code=400, detail="user_id and zip_path are required")

    config = manager.load_config(user_id, silent=True)
    if not config:
        raise HTTPException(status_code=404, detail="Consent not found for user")
    if not config.data_access_consent:
        raise HTTPException(status_code=403, detail="Data access consent not granted")

    if config.zip_file != zip_path:
        manager.update_config(user_id, zip_file=zip_path)

    use_llm = bool(config.llm_consent and config.llm_consent_asked)

    try:
      
        from src.pipeline.orchestrator import ArtifactPipeline  # type: ignore

        pipeline = ArtifactPipeline(insights_store=store)
        result = pipeline.start(
            zip_path,
            use_llm=use_llm,
            data_access_consent=True,
            prompt_project_names=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Pipeline failed") from exc

    if not result:
        raise HTTPException(status_code=400, detail="Pipeline returned no results")

    zip_hash = _resolve_zip_hash(store, zip_path)
    if not zip_hash:
      
        zip_hash = "unknown"
    project_names = [
        name for name in (result.get("projects") or {}).keys() if name != "_misc_files"
    ]

    return {"status": "ok", "zip_hash": zip_hash, "projects": project_names}


@router.get("", response_model=List[ProjectListItem])
def list_projects(
    store: ProjectInsightsStore = Depends(get_store),
):
    pipeline = PresentationPipeline(insights_store=store)
    projects = pipeline.list_available_projects()
    return [
        {
            "project_id": item["project_id"],
            "project_name": item["project_name"],
            "zip_hash": item["zip_hash"],
            "is_git_repo": item["is_git_repo"],
            "code_files": item["code_files"],
            "doc_files": item["doc_files"],
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
        }
        for item in projects
    ]


@router.get("/{project_id}")
def get_project(
    project_id: int,
    store: ProjectInsightsStore = Depends(get_store),
    role_store: ProjectRoleStore = Depends(get_role_store),
):
    payload = store.load_project_insight_by_id(project_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = PresentationPipeline(insights_store=store)._get_project_metadata(project_id)
    if metadata:
        user_role = role_store.get_user_role(metadata["zip_hash"], metadata["project_name"])
        if user_role:
            payload = dict(payload)
            payload["user_role"] = user_role
            portfolio_item = payload.get("portfolio_item")
            if isinstance(portfolio_item, dict):
                portfolio_item = dict(portfolio_item)
                portfolio_item["user_role"] = user_role
                payload["portfolio_item"] = portfolio_item
            resume_item = payload.get("resume_item")
            if isinstance(resume_item, dict):
                resume_item = dict(resume_item)
                resume_item["user_role"] = user_role
                payload["resume_item"] = resume_item

    return {"project_id": project_id, **payload}
