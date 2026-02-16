"""Resume, portfolio, and skills endpoints."""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel
from resume.resume_manager import ResumeManager
from portfolio.portfolio_manager import PortfolioManager
from portfolio.skill_mapper import SkillMapper
from common.schemas import (
    CustomWordingSaveRequest, 
    SimpleMessageResponse,
    PortfolioCustomizationRequest,
    PortfolioCustomizationResponse,
    PortfolioCustomizationListResponse
)
from project_manager import get_project_by_id
from resume.item_formatter import ItemFormatter
from portfolio.portfolio_formatter import PortfolioFormatter
from common.schemas import ResumeItemResponse, PortfolioCardResponse

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

@router.get("/resume/preview/{project_id}", response_model=ResumeItemResponse)
async def get_resume_preview(project_id: int):
    """
    Returns a single project formatted as a Resume Item (Bullet points).
    Used for the 'Edit Resume' modal or live preview.
    """
    # 1. Fetch Raw Data
    project_data = get_project_by_id(project_id)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    user_id = project_data.get('user_name', 'default') # fallback if needed
    # Note: Ideally we pass the real user_id from auth context here
    
    user_prefs = {}
    # 3. Format & Return
    return ItemFormatter.format_resume_item(project_data, user_options=user_prefs)


@router.get("/portfolio/card/{project_id}", response_model=PortfolioCardResponse)
async def get_portfolio_card(project_id: int):
    """
    Returns a single project formatted as a Portfolio Card (Rich text/Visuals).
    Used for the main Portfolio Dashboard display.
    """
    # 1. Fetch Raw Data
    project_data = get_project_by_id(project_id)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Fetch User Preferences (Placeholder for future Portfolio customization)
    user_prefs = {}

    # 3. Format & Return
    # This automatically calls your new logic + Evan's evidence extractor
    return PortfolioFormatter.format_project_card(project_data, user_options=user_prefs)

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


# Portfolio Customization Endpoints

@router.post("/portfolio/{user_id}/custom-data", response_model=PortfolioCustomizationResponse)
async def save_portfolio_customization(user_id: str, request: PortfolioCustomizationRequest):
    """Save or update portfolio customization for a specific project."""
    try:
        if request.project_id <= 0:
            raise HTTPException(status_code=400, detail="project_id must be positive")
        
        custom_data = {
            'custom_title': request.custom_title,
            'custom_description': request.custom_description,
            'custom_role': request.custom_role
        }
        
        if ResumeManager.save_portfolio_customization(user_id, request.project_id, custom_data):
            # Retrieve the saved customization to return complete data
            saved = ResumeManager.get_portfolio_customization(user_id, request.project_id)
            if saved:
                return PortfolioCustomizationResponse(
                    project_id=saved['project_id'],
                    custom_title=saved['custom_title'],
                    custom_description=saved['custom_description'],
                    custom_role=saved['custom_role'],
                    created_at=saved['created_at'].isoformat() if saved['created_at'] else None,
                    updated_at=saved['updated_at'].isoformat() if saved['updated_at'] else None
                )
        raise HTTPException(status_code=500, detail="Failed to save portfolio customization")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving portfolio customization: {str(e)}")


@router.get("/portfolio/{user_id}/custom-data", response_model=PortfolioCustomizationListResponse)
async def list_portfolio_customizations(user_id: str):
    """List all project IDs that have portfolio customizations."""
    try:
        project_ids = ResumeManager.list_customized_portfolio_projects(user_id)
        return PortfolioCustomizationListResponse(project_ids=project_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing portfolio customizations: {str(e)}")


@router.get("/portfolio/{user_id}/custom-data/{project_id}", response_model=PortfolioCustomizationResponse)
async def get_portfolio_customization(user_id: str, project_id: int):
    """Get portfolio customization for a specific project."""
    try:
        if project_id <= 0:
            raise HTTPException(status_code=400, detail="project_id must be positive")
        
        customization = ResumeManager.get_portfolio_customization(user_id, project_id)
        if customization:
            return PortfolioCustomizationResponse(
                project_id=customization['project_id'],
                custom_title=customization['custom_title'],
                custom_description=customization['custom_description'],
                custom_role=customization['custom_role'],
                created_at=customization['created_at'].isoformat() if customization['created_at'] else None,
                updated_at=customization['updated_at'].isoformat() if customization['updated_at'] else None
            )
        raise HTTPException(status_code=404, detail="Portfolio customization not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting portfolio customization: {str(e)}")


@router.delete("/portfolio/{user_id}/custom-data/{project_id}", response_model=SimpleMessageResponse)
async def clear_portfolio_customization(user_id: str, project_id: int):
    """Clear portfolio customization for a specific project."""
    try:
        if project_id <= 0:
            raise HTTPException(status_code=400, detail="project_id must be positive")
        
        if ResumeManager.clear_portfolio_customization(user_id, project_id):
            return SimpleMessageResponse(message="Portfolio customization cleared successfully")
        raise HTTPException(status_code=500, detail="Failed to clear portfolio customization")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing portfolio customization: {str(e)}")
