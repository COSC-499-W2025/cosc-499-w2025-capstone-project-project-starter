"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health
from api.routes import project
from api.routes import consent

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
app.include_router(consent.router, prefix="/api", tags=["consent"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Artifact API is running", "version": "1.0.0"}
