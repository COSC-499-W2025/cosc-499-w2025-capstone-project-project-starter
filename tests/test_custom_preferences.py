import sys
import os
import pytest

# Path Fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.resume.item_formatter import ItemFormatter
from src.portfolio.portfolio_formatter import PortfolioFormatter

@pytest.fixture
def mock_data():
    return {
        'project_info': {'filename': 'messy_project_v1.zip'},
        'languages': {'detected_languages': ['Python']},
        'file_statistics': {'total_lines_of_code': 100, 'total_files': 5},
        'project_structure': {}
    }

def test_resume_custom_overrides(mock_data):
    """Test that resume formatter respects user options."""
    options = {
        "custom_title": "Professional Title",
        "custom_role": "Architect",
        "custom_bullets": ["Built the entire backend.", "Managed DB."]
    }
    
    item = ItemFormatter.format_resume_item(mock_data, user_options=options)
    
    assert item.project_title == "Professional Title"
    assert item.role == "Architect"
    assert item.description_bullets == ["Built the entire backend.", "Managed DB."]
    # Ensure standard cleaning logic was skipped
    assert "Messy Project" not in item.project_title

def test_portfolio_custom_overrides(mock_data):
    """Test that portfolio formatter respects user options."""
    options = {
        "custom_title": "My Showcase",
        "custom_role": "Solo Dev",
        "custom_description": "This is a custom story about my project."
    }
    
    card = PortfolioFormatter.format_project_card(mock_data, user_options=options)
    
    assert card.title == "My Showcase"
    assert card.my_role == "Solo Dev"
    assert card.full_description == "This is a custom story about my project."
    # Ensure truncation logic works on custom desc
    assert "custom story" in card.short_description