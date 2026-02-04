"""FastAPI application entry point."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from api.routes import health
from api.routes import project
from api.routes import auth
import os
from api.routes import consent
from api.routes import resume_portfolio
from api.routes import settings

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
app.include_router(consent.router, prefix="/api", tags=["consent"])
app.include_router(resume_portfolio.router, prefix="/api", tags=["resume", "portfolio"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

def find_frontend_file(filename: str) -> str | None:
    """Find frontend file in various possible locations."""
    possible_paths = [
        f"/app/frontend/{filename}",  # Docker container path
        f"frontend/{filename}",        # Local development path
        f"../frontend/{filename}",     # Alternative local path
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

@app.get("/")
async def root(request: Request):
    """Serve the frontend login page or API info based on Accept header."""
    # Check if client accepts HTML (browser request)
    accept_header = request.headers.get("accept", "")
    wants_html = "text/html" in accept_header
    
    # If client wants HTML, try to serve frontend
    if wants_html:
        path = find_frontend_file("index.html")
        if path:
            return FileResponse(path)
    
    # Return JSON for API clients or if frontend not found
    return JSONResponse({
        "message": "Artifact API is running",
        "version": "1.0.0"
    })

@app.get("/index.html")
async def index_html():
    """Serve the login page."""
    path = find_frontend_file("index.html")
    if path:
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Login page not found")

@app.get("/dashboard.html")
async def dashboard():
    """Serve the dashboard page."""
    path = find_frontend_file("dashboard.html")
    if path:
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Dashboard not found")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_type, message, data = _normalize_detail(exc.detail)
    payload = {
        "success": False,
        "error_type": error_type,
        "message": message,
    }
    if data is not None:
        payload["data"] = data

    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Don't leak internal exception details to clients
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_type": "INTERNAL_ERROR",
            "message": "Internal server error",
        },
    )

def _normalize_detail(detail):
    """
    Normalize FastAPI HTTPException.detail into a unified shape.
    Supports:
      - str detail (legacy)
      - dict detail with {error_type, message, data}
      - any other types -> stringified
    """
    if isinstance(detail, dict):
        error_type = detail.get("error_type", "HTTP_ERROR")
        message = detail.get("message", "") or "Request failed"
        data = detail.get("data")
        return error_type, message, data

    if isinstance(detail, str):
        return "HTTP_ERROR", detail, None

    return "HTTP_ERROR", str(detail), None
