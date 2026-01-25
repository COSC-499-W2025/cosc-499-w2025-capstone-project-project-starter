"""Resume, portfolio, and skills endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from resume.resume_manager import ResumeManager
from portfolio.portfolio_manager import PortfolioManager
from portfolio.skill_mapper import SkillMapper
from common.schemas import CustomWordingSaveRequest, SimpleMessageResponse

router = APIRouter()


class ResumeGenerateRequest(BaseModel):
    top_projects_count: Optional[int] = 5
    selected_project_ids: Optional[list[int]] = None
    include_skills: Optional[bool] = True
    skills_mode: Optional[str] = "categorized"


class ResumeEditRequest(BaseModel):
    project_id: int
    wording: str


class PortfolioGenerateRequest(BaseModel):
    top_n: Optional[int] = None


class PortfolioEditRequest(BaseModel):
    project_id: int
    custom_data: Optional[dict] = None


@router.get("/skills")
async def get_skills(user_name: Optional[str] = Query(None)):
    """Get skills extracted from user's projects."""
    try:
        resume = ResumeManager.get_user_resume(user_name) if user_name else None
        if resume and resume.get('resume_data'):
            data = resume['resume_data']
            return {
                "success": True,
                "skills": data.get('all_skills', []),
                "categorized_skills": data.get('categorized_skills', {}),
                "languages": data.get('languages', []),
                "frameworks": data.get('frameworks', [])
            }
        return {"success": True, "skills": [], "categorized_skills": {}, "languages": [], "frameworks": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving skills: {str(e)}")


@router.get("/resume/{user_id}")
async def get_resume(user_id: str):
    """Get user's resume by ID."""
    try:
        resume = ResumeManager.get_user_resume(user_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return {"success": True, "resume": resume}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving resume: {str(e)}")


@router.post("/resume/generate")
async def generate_resume(request: ResumeGenerateRequest, user_name: Optional[str] = Query(None)):
    """Generate a new resume for the user."""
    try:
        if not user_name:
            raise HTTPException(status_code=400, detail="user_name is required")
        selection = {
            "top_projects_count": request.top_projects_count,
            "selected_project_ids": request.selected_project_ids,
            "include_skills": request.include_skills,
            "skills_mode": request.skills_mode
        } if request.selected_project_ids or request.top_projects_count != 5 else None
        resume_data = ResumeManager.generate_user_resume(user_name, request.top_projects_count, selection)
        if not resume_data:
            raise HTTPException(status_code=400, detail="Failed to generate resume. Ensure projects are uploaded.")
        if ResumeManager.store_user_resume(user_name, resume_data):
            return {"success": True, "resume": resume_data}
        raise HTTPException(status_code=500, detail="Failed to store resume")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")


@router.post("/resume/{user_id}/edit")
async def edit_resume(user_id: str, request: ResumeEditRequest):
    """Edit custom wording for a project in the resume."""
    try:
        if ResumeManager.save_custom_project_wording(user_id, request.project_id, request.wording):
            return {"success": True, "message": "Resume updated"}
        raise HTTPException(status_code=500, detail="Failed to update resume")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing resume: {str(e)}")

@router.get("/resume/{user_id}/custom-wording")
async def list_resume_custom_wording(user_id: str):
    """List project_ids that have custom wording saved."""
    try:
        project_ids = ResumeManager.list_custom_worded_projects(user_id)
        return {"success": True, "project_ids": project_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing custom wording: {str(e)}")


@router.post("/resume/{user_id}/custom-wording")
async def save_resume_custom_wording(user_id: str, request: CustomWordingSaveRequest):
    """
    Save or overwrite custom wording for a project using a dedicated request schema.
    """
    try:
        if request.project_id <= 0:
            raise HTTPException(status_code=400, detail="project_id must be positive")

        if ResumeManager.save_custom_project_wording(user_id, request.project_id, request.wording):
            return {"success": True, "message": "Custom wording saved"}
        raise HTTPException(status_code=500, detail="Failed to save custom wording")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving custom wording: {str(e)}")


@router.delete("/resume/{user_id}/custom-wording/{project_id}")
async def clear_resume_custom_wording(user_id: str, project_id: int):
    """Clear custom wording for a project."""
    try:
        if project_id <= 0:
            raise HTTPException(status_code=400, detail="project_id must be positive")

        if ResumeManager.clear_custom_project_wording(user_id, project_id):
            return {"success": True, "message": "Custom wording cleared"}
        raise HTTPException(status_code=500, detail="Failed to clear custom wording")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing custom wording: {str(e)}")


@router.delete("/resume/{user_id}")
async def delete_resume(user_id: str):
    """Delete user's resume."""
    try:
        if ResumeManager.delete_user_resume(user_id):
            return {"success": True, "message": "Resume deleted"}
        raise HTTPException(status_code=500, detail="Failed to delete resume")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting resume: {str(e)}")


@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str, top_n: Optional[int] = Query(None)):
    """Get user's portfolio by ID."""
    try:
        manager = PortfolioManager(user_id)
        portfolio_data = manager.generate_portfolio_report(top_n=top_n)
        if 'error' in portfolio_data:
            raise HTTPException(status_code=404, detail=portfolio_data['error'])
        return {"success": True, "portfolio": portfolio_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving portfolio: {str(e)}")


@router.post("/portfolio/generate")
async def generate_portfolio(request: PortfolioGenerateRequest, user_name: Optional[str] = Query(None)):
    """Generate a new portfolio for the user."""
    try:
        if not user_name:
            raise HTTPException(status_code=400, detail="user_name is required")
        manager = PortfolioManager(user_name)
        portfolio_data = manager.generate_portfolio_report(top_n=request.top_n)
        if 'error' in portfolio_data:
            raise HTTPException(status_code=400, detail=portfolio_data['error'])
        return {"success": True, "portfolio": portfolio_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating portfolio: {str(e)}")


@router.post("/portfolio/{user_id}/edit")
async def edit_portfolio(user_id: str, request: PortfolioEditRequest):
    """Edit portfolio custom data (placeholder for future enhancements)."""
    try:
        return {"success": True, "message": "Portfolio edit feature coming soon"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing portfolio: {str(e)}")
