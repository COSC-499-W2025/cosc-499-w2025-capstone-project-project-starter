"""Project-related endpoints."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/projects")
async def get_projects():
    """Get projects list - verification endpoint."""
    return {
        "message": "Projects endpoint is working",
        "projects": []
    }
