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

    Important: This schema intentionally separates **verified** data
    (derived from analysis/DB) from user-controlled narrative/layout data.
    Narrative fields are editable; verified fields are read-only on the client.
    """
    # Stable identifier (DB-backed, not user editable)
    project_id: str

    # Narrative / presentation (user controllable)
    title: str
    short_description: str = Field(
        ...,
        max_length=250,
        description="One-line elevator pitch (user editable narrative, not source-of-truth)",
    )
    full_description: str

    # Visuals
    image_url: Optional[str] = Field(
        None,
        description="URL or Path to the showcase image (customizable display only)",
    )

    # Metadata for rich display (links are user provided)
    repo_link: Optional[str] = None
    live_link: Optional[str] = None

    # Collaborative details
    my_role: str  # narrative role label; underlying collab data lives in analysis results
    collaborators: List[str] = Field(default_factory=list)

    # Evidence of Success (Metrics) – narrative layer, not raw metrics
    success_metrics: List[str] = Field(
        default_factory=list,
        description="Narrative achievements (e.g., '4.5/5 User Rating', '90% Test Coverage')",
    )

    # Technologies for visual chips (built from verified analysis but safe to render)
    technologies: List[TechStack]

    # ---- Verified, derived fields (read-only for clients) ----
    primary_language: Optional[str] = Field(
        None,
        description="Primary language detected from analysis (read-only, DB derived)",
    )
    languages: List[str] = Field(
        default_factory=list,
        description="All languages detected from analysis (read-only, DB derived)",
    )
    frameworks: List[str] = Field(
        default_factory=list,
        description="Detected frameworks/libraries (read-only, DB derived)",
    )
    has_tests: Optional[bool] = Field(
        None,
        description="Whether tests were detected in the project (read-only, analysis derived)",
    )
    has_docs: Optional[bool] = Field(
        None,
        description="Whether documentation files were detected (read-only, analysis derived)",
    )
    lines_of_code: Optional[int] = Field(
        None,
        description="Approximate total lines of code (read-only, analysis derived)",
    )
    file_count: Optional[int] = Field(
        None,
        description="Total file count (read-only, analysis derived)",
    )

    # Ranking / evaluation signals (derived from ranking system; no leaderboard UI)
    verified_score: Optional[float] = Field(
        None,
        description="Composite normalized score from ranking engine (read-only, 0–100)",
    )
    score_tier: Optional[str] = Field(
        None,
        description="Coarse-grained evaluation band derived from score (e.g. 'top', 'strong', 'developing')",
    )
    evaluation_insights: List[str] = Field(
        default_factory=list,
        description="Short, human-readable highlights/risks derived from analysis (read-only)",
    )
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


class PortfolioCustomizationRequest(BaseModel):
    """Request schema for saving portfolio project customizations."""
    project_id: int = Field(..., ge=1, description="Project ID to customize")
    custom_title: Optional[str] = Field(None, description="Custom title for the portfolio project")
    custom_description: Optional[str] = Field(None, description="Custom description for the portfolio project")
    custom_role: Optional[str] = Field(None, description="Custom role description for the portfolio project")
    display_order: Optional[int] = Field(
        None,
        ge=0,
        description="Optional explicit display order for this project within the portfolio.",
    )
    highlight: Optional[bool] = Field(
        None,
        description="Whether this project should be visually highlighted/featured in the portfolio layout.",
    )


class PortfolioCustomizationResponse(BaseModel):
    """Response schema for portfolio project customization."""
    success: bool = True
    project_id: int
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    custom_role: Optional[str] = None
    display_order: Optional[int] = None
    highlight: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioCustomizationListResponse(BaseModel):
    """Response schema for listing customized portfolio projects."""
    success: bool = True
    project_ids: List[int] = Field(default_factory=list)


class SimpleMessageResponse(BaseModel):
    success: bool = True
    message: str
