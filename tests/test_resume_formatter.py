import pytest
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from resume.resume_formatter import ResumeFormatter
class TestResumeFormatterJSON:
    """Test JSON formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'user_id': 'test_user',
            'total_projects_analyzed': 10,
            'top_projects_displayed': 5,
            'all_skills': ['Python', 'JavaScript', 'React'],
            'top_projects': [
                {
                    'project_name': 'Project 1',
                    'score': 95,
                    'project_type': 'web',
                    'skills': ['Python', 'React']
                }
            ],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_format_json_success(self, sample_resume):
        """Test successful JSON formatting."""
        result = ResumeFormatter.format_json(sample_resume)
        
        assert result is not None
        assert isinstance(result, str)
        assert '"user_id"' in result
        assert '"total_projects_analyzed"' in result
    
    def test_format_json_empty_data(self):
        """Test JSON formatting with empty data."""
        result = ResumeFormatter.format_json(None)
        
        assert result is None
    
    def test_format_json_parses_back(self, sample_resume):
        """Test that formatted JSON can be parsed back."""
        import json
        formatted = ResumeFormatter.format_json(sample_resume)
        
        parsed = json.loads(formatted)
        assert parsed['user_id'] == 'test_user'
        assert parsed['total_projects_analyzed'] == 10


class TestResumeFormatterMarkdown:
    """Test Markdown formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'total_projects_analyzed': 10,
            'top_projects_displayed': 2,
            'all_skills': ['Python', 'JavaScript'],
            'top_projects': [
                {
                    'project_name': 'Project A',
                    'score': 95,
                    'project_type': 'backend',
                    'skills': ['Python']
                }
            ],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_format_markdown_success(self, sample_resume):
        """Test successful Markdown formatting."""
        result = ResumeFormatter.format_markdown(sample_resume)
        
        assert result is not None
        assert '# Resume' in result
        assert '## Overview' in result
        assert 'Python' in result
        assert 'Project A' in result
    
    def test_format_markdown_contains_sections(self, sample_resume):
        """Test that Markdown contains all required sections."""
        result = ResumeFormatter.format_markdown(sample_resume)
        
        assert '## Skills' in result
        assert '## Top Projects' in result
        assert 'Technologies:' in result


class TestResumeFormatterText:
    """Test plain text formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'total_projects_analyzed': 5,
            'top_projects_displayed': 1,
            'all_skills': ['Java', 'Spring'],
            'top_projects': [
                {
                    'project_name': 'Backend Service',
                    'score': 88,
                    'project_type': 'backend',
                    'skills': ['Java', 'Spring']
                }
            ],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_format_text_success(self, sample_resume):
        """Test successful text formatting."""
        result = ResumeFormatter.format_text(sample_resume)
        
        assert result is not None
        assert 'RESUME' in result
        assert 'OVERVIEW:' in result
        assert 'SKILLS:' in result
        assert 'TOP PROJECTS:' in result
    
    def test_format_text_contains_data(self, sample_resume):
        """Test that text format contains actual data."""
        result = ResumeFormatter.format_text(sample_resume)
        
        assert 'Java' in result
        assert 'Backend Service' in result
        assert '88' in result


class TestResumeFormatterInterface:
    """Test main formatter interface."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'total_projects_analyzed': 3,
            'top_projects_displayed': 1,
            'all_skills': ['Python'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_get_formatted_resume_json(self, sample_resume):
        """Test getting resume in JSON format."""
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'json')
        
        assert result is not None
        assert isinstance(result, str)
    
    def test_get_formatted_resume_markdown(self, sample_resume):
        """Test getting resume in Markdown format."""
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'markdown')
        
        assert result is not None
        assert '# Resume' in result
    
    def test_get_formatted_resume_text(self, sample_resume):
        """Test getting resume in text format."""
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'text')
        
        assert result is not None
        assert 'RESUME' in result
    
    def test_get_formatted_resume_default_format(self, sample_resume):
        """Test default format is text."""
        result = ResumeFormatter.get_formatted_resume(sample_resume)
        
        assert result is not None
        assert 'RESUME' in result
    
    def test_get_formatted_resume_invalid_format(self, sample_resume):
        """Test invalid format defaults to text."""
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'invalid')
        
        assert result is not None
        assert 'RESUME' in result