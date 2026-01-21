"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import health
from api.routes import project
from api.routes import auth
import os

app = FastAPI(
    title="Artifact API",
    description="Backend API for artifact analysis and portfolio management",
    version="1.0.0"
)

# CORS middleware for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(project.router, prefix="/api", tags=["projects"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])


@app.get("/")
async def serve_frontend():
    """Serve the frontend login page."""
    # Try multiple possible paths for the frontend
    possible_paths = [
        "/app/frontend/index.html",  # Docker container path
        "frontend/index.html",        # Local development path
        "../frontend/index.html",     # Alternative local path
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path)
    
    # Fallback to API info if frontend not found
    return {"message": "Artifact API is running", "version": "1.0.0"}
