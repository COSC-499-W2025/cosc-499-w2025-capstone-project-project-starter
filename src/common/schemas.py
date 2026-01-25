from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# --- Shared Models ---
class TechStack(BaseModel):
    """Represents a technology or skill used in the project."""
    name: str
    category: Optional[str] = None  # e.g., "Language", "Framework", "Tool"

# --- Resume Specific Models ---
class ResumeItemResponse(BaseModel):
    """
    Output schema for a project formatted as a Resume item.
    Optimized for text-heavy, bullet-point presentation.
    """
    project_title: str
    role: str = Field(..., description="The user's specific role in the project (e.g. 'Backend Lead')")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # The core content: succinct bullet points
    description_bullets: List[str] = Field(..., description="List of action-oriented summary strings")
    
    technologies: List[str] = Field(default_factory=list, description="List of tech names only for brevity")
    
    # Pydantic V2 Configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_title": "Capstone Portfolio Manager",
                "role": "Backend Engineer",
                "start_date": "Jan 2025",
                "end_date": "Apr 2025",
                "description_bullets": [
                    "Designed scalable REST API using FastAPI serving 100+ requests.",
                    "Optimized database queries reducing latency by 40%."
                ],
                "technologies": ["Python", "FastAPI", "Docker"]
            }
        }
    )

# --- Portfolio Specific Models ---
class PortfolioCardResponse(BaseModel):
    """
    Output schema for a project formatted as a Portfolio Showcase card.
    Optimized for visual presentation with images and metrics.
    """
    project_id: str
    title: str
    short_description: str = Field(..., max_length=250, description="One-line elevator pitch")
    full_description: str
    
    # Visuals
    image_url: Optional[str] = Field(None, description="URL or Path to the showcase image (Evan's module)")
    
    # Metadata for rich display
    repo_link: Optional[str] = None
    live_link: Optional[str] = None
    
    # Collaborative details
    my_role: str
    collaborators: List[str] = Field(default_factory=list)
    
    # Evidence of Success (Metrics)
    success_metrics: List[str] = Field(
        default_factory=list, 
        description="Quantifiable achievements (e.g., '4.5/5 User Rating', '90% Test Coverage')"
    )
    
    technologies: List[TechStack]  # More detailed than resume, includes categories if available
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "proj_123",
                "title": "Crypto Trading Bot",
                "short_description": "Automated trading bot using moving average crossovers.",
                "full_description": "A complete solution for...",
                "image_url": "/static/images/proj_123_thumb.png",
                "my_role": "Solo Developer",
                "success_metrics": ["$500 Profit in Month 1", "Zero Downtime"],
                "technologies": [{"name": "Python", "category": "Language"}]
            }
        }
    )

class CustomWordingSaveRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    wording: str = Field(..., description="Custom résumé wording for this project")


class CustomWordingListResponse(BaseModel):
    success: bool = True
    project_ids: List[int] = Field(default_factory=list)


class SimpleMessageResponse(BaseModel):
    success: bool = True
    message: str
