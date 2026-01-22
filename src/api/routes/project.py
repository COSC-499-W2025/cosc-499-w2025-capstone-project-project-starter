"""Project-related endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Optional
import json
import tempfile
import os
from upload_file import add_file_to_db, list_uploaded_files
from project_manager import list_projects, get_project_by_id
from project_analyzer import analyze_project_by_id
from analysis.project_ranking import rank_all_projects, save_rankings_with_summaries, rank_and_summarize_top_projects
from analysis.ranking_storage import get_stored_rankings
from tools.cleanup_insights import delete_insights
from database.user_preferences import update_user_git_username, get_user_git_username

router = APIRouter()


@router.post("/projects/upload")
async def upload_project(
    file: UploadFile = File(...),
    user_name: Optional[str] = Query(None, description="Username for the upload")
):
    """
    Upload a project file (ZIP archive).
    
    Args:
        file: The ZIP file to upload
        user_name: Optional username (defaults to None if not provided)
        
    Returns:
        dict: Upload result with file information
    """
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported"
        )
    
    # Create temporary file to save upload
    temp_file = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Use existing upload function
        result = add_file_to_db(temp_path, user_name=user_name)
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.message
            )
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up temp file on error
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/projects")
async def get_projects(
    user_name: Optional[str] = Query(None, description="Filter projects by username")
):
    """
    Get list of all projects.
    
    Args:
        user_name: Optional username to filter projects (if not provided, returns all)
        
    Returns:
        dict: List of projects with metadata
    """
    try:
        if user_name:
            # Use project_manager for user-specific projects
            # list_projects returns a list of dicts, so we use it directly
            projects = list_projects(user_name=user_name)
            # Convert datetime objects to ISO strings for API response
            for proj in projects:
                created_at = proj.get('created_at')
                if created_at:
                    if hasattr(created_at, 'isoformat'):
                        proj['created_at'] = created_at.isoformat()
                    else:
                        proj['created_at'] = str(created_at)
        else:
            # Get all projects from uploaded_files
            projects_data = list_uploaded_files()
            projects = []
            for proj in projects_data:
                # Parse metadata to get file count
                file_count = 0
                if proj.get('metadata'):
                    try:
                        metadata = json.loads(proj['metadata']) if isinstance(proj['metadata'], str) else proj['metadata']
                        if 'files' in metadata and metadata['files']:
                            actual_files = [f for f in metadata['files'] if not f.endswith('/')]
                            file_count = len(actual_files)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Handle datetime conversion
                created_at = proj.get('created_at')
                if created_at:
                    if hasattr(created_at, 'isoformat'):
                        # datetime object
                        created_at_str = created_at.isoformat()
                    else:
                        # Already a string
                        created_at_str = str(created_at)
                else:
                    created_at_str = None
                
                projects.append({
                    'id': proj['id'],
                    'filename': proj['filename'],
                    'created_at': created_at_str,
                    'file_count': file_count,
                    'status': proj.get('status', 'unknown')
                })
        
        return {
            "success": True,
            "count": len(projects),
            "projects": projects
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving projects: {str(e)}"
        )


@router.get("/projects/{project_id}")
async def get_project_by_id_endpoint(
    project_id: int,
    user_name: Optional[str] = Query(None, description="Username to verify project ownership")
):
    """
    Get a specific project by ID.
    
    Args:
        project_id: The ID of the project to retrieve
        user_name: Optional username to verify ownership
        
    Returns:
        dict: Project information
    """
    try:
        project = get_project_by_id(project_id, user_name=user_name)
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Convert datetime to ISO format string (handle both datetime objects and strings)
        created_at = project.get('created_at')
        if created_at:
            if hasattr(created_at, 'isoformat'):
                # datetime object
                created_at_str = created_at.isoformat()
            else:
                # Already a string
                created_at_str = str(created_at)
        else:
            created_at_str = None
        
        project_data = {
            'id': project['id'],
            'filename': project['filename'],
            'filepath': project['filepath'],
            'status': project['status'],
            'metadata': project['metadata'],
            'created_at': created_at_str
        }
        
        return {
            "success": True,
            "project": project_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving project: {str(e)}"
        )


@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int, user_name: Optional[str] = Query(None)):
    """Analyze a project."""
    try:
        from project_analyzer import ProjectAnalyzer
        analyzer = ProjectAnalyzer(user_name or 'default_user')
        results = analyzer.analyze_uploaded_project(project_id)
        if not results.get('success'):
            raise HTTPException(status_code=400, detail=results.get('error', 'Analysis failed'))
        return {"success": True, "analysis": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing project: {str(e)}")


@router.post("/projects/rank")
async def rank_projects(user_name: Optional[str] = Query(None)):
    """Rank all projects."""
    try:
        ranked = rank_all_projects(user_name=user_name)
        save_rankings_with_summaries(ranked, generate_summaries=True)
        return {"success": True, "ranked_projects": ranked[:10], "count": len(ranked)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ranking projects: {str(e)}")


@router.post("/projects/rank-top3")
async def rank_top3(user_name: Optional[str] = Query(None)):
    """Rank and summarize top 3 projects."""
    try:
        rank_and_summarize_top_projects()
        ranked = rank_all_projects(user_name=user_name)
        return {"success": True, "top3": ranked[:3]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ranking top 3: {str(e)}")


@router.get("/projects/rankings")
async def get_rankings():
    """Get stored rankings."""
    try:
        rankings = get_stored_rankings()
        return {"success": True, "rankings": rankings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving rankings: {str(e)}")


@router.delete("/projects/{project_id}/insights")
async def cleanup_project_insights(project_id: int):
    """Delete project insights."""
    try:
        deleted = delete_insights(project_id)
        return {"success": True, "deleted": {"metrics": deleted[0], "files": deleted[1], "projects": deleted[2]}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up insights: {str(e)}")


@router.post("/preferences")
async def update_preferences(request: dict):
    """Update user preferences."""
    try:
        git_username = request.get('git_username')
        if git_username:
            update_user_git_username(git_username)
        return {"success": True, "git_username": get_user_git_username()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating preferences: {str(e)}")
