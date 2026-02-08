from __future__ import annotations

from typing import List, Set

from fastapi import APIRouter, Depends

from src.api.deps import get_store
from src.insights.storage import ProjectInsightsStore
from src.pipeline.presentation_pipeline import PresentationPipeline

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
def list_skills(store: ProjectInsightsStore = Depends(get_store)) -> List[str]:
    pipeline = PresentationPipeline(insights_store=store)
    projects = pipeline.list_available_projects()
    skills: Set[str] = set()
    for item in projects:
        pid = item.get("project_id")
        if not isinstance(pid, int):
            continue
        payload = store.load_project_insight_by_id(pid)
        if not payload:
            continue
        metrics = payload.get("project_metrics") or {}
        for s in metrics.get("skills", []) or []:
            if isinstance(s, str) and s.strip():
                skills.add(s.strip())
    return sorted(skills)
