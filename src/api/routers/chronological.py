from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.deps import get_store
from src.insights.storage import ProjectInsightsStore

router = APIRouter(prefix="/chronological", tags=["chronological"])


class SkillEvent(BaseModel):
    """A single skill event in the timeline."""
    file: str
    timestamp: str
    category: str
    skills: List[str]
    metadata: dict = {}


class ChronologicalSkillsResponse(BaseModel):
    """Chronological skills timeline response."""
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    zip_hash: str
    total_events: int
    categories: List[str]
    timeline: List[SkillEvent]


class ChronologicalProjectsResponse(BaseModel):
    """Chronological list of projects."""
    total_projects: int
    projects: List[dict]


@router.get("/skills", response_model=ChronologicalSkillsResponse)
def get_chronological_skills(
    zip_hash: Optional[str] = Query(None, description="ZIP hash (default: most recent)"),
    project_name: Optional[str] = Query(None, description="Project name (default: first project)"),
    store: ProjectInsightsStore = Depends(get_store),
):
    """
    Get chronological skills timeline for a project.
    
    Shows when each skill was exercised, ordered by timestamp.
    """
    # Get ZIP hash
    if not zip_hash:
        runs = store.list_recent_zipfiles(limit=1)
        if not runs:
            raise HTTPException(
                status_code=404,
                detail="No pipeline runs found. Run the pipeline first."
            )
        zip_hash = runs[0]["zip_hash"]
    
    # Get project name
    projects = store.list_projects_for_zip(zip_hash)
    if not projects:
        raise HTTPException(
            status_code=404,
            detail=f"No projects found for ZIP hash: {zip_hash}"
        )
    
    if not project_name:
        # Get first non-misc project
        project_name = next((p for p in projects if p != "_misc_files"), projects[0])
    
    # Load chronological skills
    try:
        payload = store.load_project_insight(zip_hash, project_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading project insights: {str(e)}"
        )
    
    global_insights = payload.get("global_insights", {})
    chron_skills = global_insights.get("chronological_skills", {})
    
    if not chron_skills or not chron_skills.get("timeline"):
        raise HTTPException(
            status_code=404,
            detail=f"No chronological skills found for project: {project_name}"
        )
    
    # Get project_id if available
    project_id = payload.get("project_id")
    
    return ChronologicalSkillsResponse(
        project_id=project_id,
        project_name=project_name,
        zip_hash=zip_hash,
        total_events=chron_skills.get("total_events", 0),
        categories=chron_skills.get("categories", []),
        timeline=[
            SkillEvent(
                file=event["file"],
                timestamp=event["timestamp"],
                category=event["category"],
                skills=event["skills"],
                metadata=event.get("metadata", {})
            )
            for event in chron_skills.get("timeline", [])
        ]
    )


@router.get("/skills/{project_id}", response_model=ChronologicalSkillsResponse)
def get_chronological_skills_by_project_id(
    project_id: int,
    store: ProjectInsightsStore = Depends(get_store),
):
    """
    Get chronological skills timeline for a project by project ID.
    
    This is a convenience endpoint that uses project_id instead of zip_hash + project_name.
    """
    # Load project by ID
    try:
        payload = store.load_project_insight_by_id(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading project insights: {str(e)}"
        )
    
    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Get chronological skills
    global_insights = payload.get("global_insights", {})
    chron_skills = global_insights.get("chronological_skills", {})
    
    if not chron_skills or not chron_skills.get("timeline"):
        raise HTTPException(
            status_code=404,
            detail=f"No chronological skills found for project ID: {project_id}"
        )
    
    project_name = payload.get("project_name", "Unknown")
    
    # Get zip_hash from metadata
    from src.pipeline.presentation_pipeline import PresentationPipeline
    metadata = PresentationPipeline(insights_store=store)._get_project_metadata(project_id)
    zip_hash = metadata.get("zip_hash", "") if metadata else ""
    
    return ChronologicalSkillsResponse(
        project_id=project_id,
        project_name=project_name,
        zip_hash=zip_hash,
        total_events=chron_skills.get("total_events", 0),
        categories=chron_skills.get("categories", []),
        timeline=[
            SkillEvent(
                file=event["file"],
                timestamp=event["timestamp"],
                category=event["category"],
                skills=event["skills"],
                metadata=event.get("metadata", {})
            )
            for event in chron_skills.get("timeline", [])
        ]
    )


@router.get("/projects", response_model=ChronologicalProjectsResponse)
def get_chronological_projects(
    limit: int = Query(50, description="Maximum number of projects to return"),
    store: ProjectInsightsStore = Depends(get_store),
):
    """
    Get chronological list of all projects, ordered by creation date.
    
    Returns projects from all ZIP files, sorted by when they were analyzed.
    """
    # Get all recent ZIP files
    runs = store.list_recent_zipfiles(limit=limit)
    
    if not runs:
        return ChronologicalProjectsResponse(
            total_projects=0,
            projects=[]
        )
    
    # Collect all projects from all runs
    all_projects = []
    
    for run in runs:
        zip_hash = run["zip_hash"]
        zip_path = run["zip_path"]
        created_at = run["created_at"]
        
        # Get projects for this ZIP
        projects = store.list_projects_for_zip(zip_hash)
        
        for project_name in projects:
            if project_name == "_misc_files":
                continue
            
            try:
                payload = store.load_project_insight(zip_hash, project_name)
                
                all_projects.append({
                    "project_name": project_name,
                    "zip_hash": zip_hash,
                    "zip_path": zip_path,
                    "created_at": created_at,
                    "is_git_repo": payload.get("is_git_repo", False),
                    "languages": payload.get("analysis_results", {}).get("code", {}).get("metrics", {}).get("languages", []),
                    "total_commits": payload.get("git_analysis", {}).get("total_commits", 0),
                    "total_contributors": payload.get("git_analysis", {}).get("total_contributors", 0),
                })
            except Exception:
                # Skip projects that can't be loaded
                continue
    
    return ChronologicalProjectsResponse(
        total_projects=len(all_projects),
        projects=all_projects
    )

