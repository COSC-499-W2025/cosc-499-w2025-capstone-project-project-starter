import sys
import os
import pytest
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from resume.item_formatter import ItemFormatter
from common.schemas import ResumeItemResponse
from common.utils import clean_project_title

@pytest.fixture
def sample_project_data():
    return {
        'project_info': {
            'filename': 'ecommerce-backend-main.zip',
            'created_at': '2025-01-15T10:00:00'
        },
        'languages': {'detected_languages': ['Python', 'SQL']},
        'frameworks': ['Django', 'DRF'],
        'file_statistics': {
            'total_lines_of_code': 1500,
            'total_files': 45
        },
        'project_structure': {
            'has_tests': True,
            'has_docs': False
        }
    }

def test_format_resume_item_structure(sample_project_data):
    """Ensure the output matches the Pydantic schema."""
    result = ItemFormatter.format_resume_item(sample_project_data)
    
    assert isinstance(result, ResumeItemResponse)
    assert result.project_title == "Ecommerce Backend"
    assert result.role == "Software Developer"
    assert "Django" in result.technologies
    assert "Python" in result.technologies

def test_name_cleaning():
    assert clean_project_title("my-cool_project-main.zip") == "My Cool Project"
    assert clean_project_title("simple_app") == "Simple App"

def test_bullet_generation(sample_project_data):
    """Check that bullets include metrics."""
    result = ItemFormatter.format_resume_item(sample_project_data)
    bullets = result.description_bullets
    assert any("1500+ lines" in b for b in bullets)
    assert any("unit tests" in b for b in bullets)

def test_missing_data_handling():
    """Test resilience against empty data."""
    empty_data = {'project_info': {}}
    result = ItemFormatter.format_resume_item(empty_data)
    
    assert result.project_title == "Untitled Project"
    assert result.start_date == "N/A"
    assert len(result.description_bullets) >= 1