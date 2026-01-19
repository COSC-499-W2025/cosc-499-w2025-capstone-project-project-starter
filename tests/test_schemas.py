import pytest
from pydantic import ValidationError
from src.common.schemas import ResumeItemResponse, PortfolioCardResponse, TechStack

def test_resume_item_valid_creation():
    """Test creating a ResumeItemResponse with valid data."""
    data = {
        "project_title": "Test Project",
        "role": "Developer",
        "description_bullets": ["Did a thing", "Did another thing"],
        "technologies": ["Python", "Pytest"]
    }
    item = ResumeItemResponse(**data)
    assert item.project_title == "Test Project"
    assert len(item.description_bullets) == 2
    assert item.role == "Developer"

def test_resume_item_missing_field():
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        # Missing 'description_bullets' and 'role'
        ResumeItemResponse(project_title="Incomplete Project")

def test_portfolio_card_valid_creation():
    """Test creating a PortfolioCardResponse with valid data."""
    data = {
        "project_id": "p1",
        "title": "Portfolio App",
        "short_description": "A cool app",
        "full_description": "A very cool app that does many things.",
        "my_role": "Lead",
        "technologies": [{"name": "React", "category": "Frontend"}]
    }
    card = PortfolioCardResponse(**data)
    assert card.project_id == "p1"
    assert card.technologies[0].name == "React"
    assert card.image_url is None  # Optional field should be None by default

def test_portfolio_card_metrics_default():
    """Ensure success_metrics defaults to empty list if not provided."""
    data = {
        "project_id": "p2",
        "title": "App 2",
        "short_description": "Desc",
        "full_description": "Full Desc",
        "my_role": "Dev",
        "technologies": []
    }
    card = PortfolioCardResponse(**data)
    assert card.success_metrics == []
    assert isinstance(card.collaborators, list)