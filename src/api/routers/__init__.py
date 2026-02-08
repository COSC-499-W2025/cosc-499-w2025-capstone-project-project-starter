from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.portfolio import router as portfolio_router
from src.api.routers.privacy import router as privacy_router
from src.api.routers.projects import router as projects_router
from src.api.routers.chronological import router as chronological_router
from src.api.routers.resume import router as resume_router
from src.api.routers.skills import router as skills_router

api_router = APIRouter()
api_router.include_router(privacy_router)
api_router.include_router(projects_router)
api_router.include_router(portfolio_router)
api_router.include_router(chronological_router)
api_router.include_router(resume_router)
api_router.include_router(skills_router)

__all__ = ["api_router"]
