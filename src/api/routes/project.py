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
        
        # Use existing upload function, passing the original filename
        result = add_file_to_db(temp_path, user_name=user_name, original_filename=file.filename)
        
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
    """Analyze a project using local analysis."""
    try:
        from project_analyzer import ProjectAnalyzer
        # Use interactive=False to skip stdin prompts in API context
        analyzer = ProjectAnalyzer(user_name or 'default_user', interactive=False)
        results = analyzer.analyze_uploaded_project(project_id)
        if not results.get('success'):
            raise HTTPException(status_code=400, detail=results.get('error', 'Analysis failed'))
        return {"success": True, "analysis": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing project: {str(e)}")


@router.post("/projects/{project_id}/analyze-gemini")
async def analyze_project_gemini(project_id: int, user_name: Optional[str] = Query(None)):
    """
    Perform deep AI-powered analysis using Gemini.
    
    This provides a more thorough analysis than the local analysis,
    including architecture assessment, skill evaluation, security review,
    and actionable recommendations.
    """
    try:
        from project_manager import get_project_by_id
        from analysis.gemini_analyzer import GeminiAnalyzer
        from config.db_config import with_db_cursor
        
        # Get project info
        project = get_project_by_id(project_id, user_name=user_name)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # Get file contents from database
        file_contents = []
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT file_path, file_name, file_extension, file_size,
                       file_content, content_type, is_binary
                FROM file_contents
                WHERE uploaded_file_id = %s
                ORDER BY file_path
            """, (project_id,))
            
            for row in cursor.fetchall():
                file_contents.append({
                    'file_path': row[0],
                    'file_name': row[1],
                    'file_extension': row[2],
                    'file_size': row[3] or 0,
                    'file_content': row[4],
                    'content_type': row[5],
                    'is_binary': row[6],
                })
        
        if not file_contents:
            raise HTTPException(status_code=400, detail="No file contents found for this project")
        
        # Get basic context from local analysis for Gemini
        from project_analyzer import ProjectAnalyzer
        local_analyzer = ProjectAnalyzer(user_name or 'default_user', interactive=False)
        languages = local_analyzer._analyze_languages_from_files(file_contents)
        frameworks = local_analyzer._detect_frameworks_from_files(file_contents)
        
        context = {
            'primary_language': languages.get('primary_language'),
            'detected_languages': languages.get('detected_languages', []),
            'frameworks': frameworks,
        }
        
        # Run Gemini analysis
        analyzer = GeminiAnalyzer()
        results = analyzer.analyze_project(
            file_contents,
            project_name=project['filename'],
            project_context=context
        )
        
        if not results.get('success'):
            raise HTTPException(status_code=400, detail=results.get('error', 'Gemini analysis failed'))
        
        # Store results in database (creates new record for each analysis)
        try:
            with with_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO analysis_results (uploaded_file_id, analysis_data, analysis_strategy)
                    VALUES (%s, %s, %s)
                """, (project_id, json.dumps(results, default=str), 'gemini'))
        except Exception as db_err:
            # Log but don't fail - analysis was successful
            print(f"Warning: Could not store Gemini analysis results: {db_err}")
        
        return {"success": True, "analysis": results, "analysis_type": "gemini"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in Gemini analysis: {str(e)}")


@router.post("/projects/{project_id}/quick-summary")
async def get_project_quick_summary(project_id: int, user_name: Optional[str] = Query(None)):
    """
    Get a quick AI-generated summary of a project.
    Useful for resume/portfolio descriptions.
    """
    try:
        from project_manager import get_project_by_id
        from analysis.gemini_analyzer import GeminiAnalyzer
        from config.db_config import with_db_cursor
        
        # Get project info
        project = get_project_by_id(project_id, user_name=user_name)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        # Get file contents
        file_contents = []
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT file_path, file_name, file_extension, file_size,
                       file_content, content_type, is_binary
                FROM file_contents
                WHERE uploaded_file_id = %s
            """, (project_id,))
            
            for row in cursor.fetchall():
                file_contents.append({
                    'file_path': row[0],
                    'file_name': row[1],
                    'file_extension': row[2],
                    'file_size': row[3] or 0,
                    'file_content': row[4],
                    'content_type': row[5],
                    'is_binary': row[6],
                })
        
        if not file_contents:
            raise HTTPException(status_code=400, detail="No file contents found")
        
        analyzer = GeminiAnalyzer()
        summary = analyzer.get_quick_summary(file_contents, project['filename'])
        
        return {"success": True, "summary": summary, "project_name": project['filename']}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


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


@router.delete("/projects/{project_id}/data")
async def delete_project_data(
    project_id: int,
    user_name: Optional[str] = Query(None, description="Username for data isolation verification")
):
    """Delete all project data including metrics, file contents, and project records.
    
    Args:
        project_id: ID of the project to delete
        user_name: Username to verify project ownership (required for security)
    
    Returns:
        dict: Success status and deletion statistics
    
    Raises:
        HTTPException: 400 if user_name not provided, 403 if permission denied, 500 on error
    """
    # Require user_name for security
    if not user_name:
        raise HTTPException(
            status_code=400,
            detail="user_name parameter is required for data isolation"
        )
    
    try:
        deleted = delete_insights(project_id, user_name=user_name)
        return {
            "success": True,
            "deleted": {
                "metrics": deleted[0],
                "files": deleted[1],
                "projects": deleted[2]
            }
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting project data: {str(e)}")


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
