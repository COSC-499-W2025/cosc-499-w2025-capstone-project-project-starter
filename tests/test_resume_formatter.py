"""
Tests for ResumeFormatter functionality.
Tests JSON, Markdown, Text, and PDF formatting of resume data.
"""
import pytest
import sys
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.resume_formatter import ResumeFormatter


class TestResumeFormatterJSON:
    """Test JSON formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'user_name': 'test_user',
            'total_projects_analyzed': 10,
            'top_projects_displayed': 5,
            'all_skills': ['Python', 'JavaScript', 'React'],
            'summary_stats': {
                'total_lines_of_code': 5000,
                'total_files': 50,
                'unique_languages': 3,
                'unique_frameworks': 2
            },
            'categorized_skills': {
                'Languages': ['Python', 'JavaScript'],
                'Frameworks': ['React']
            },
            'languages': ['Python', 'JavaScript'],
            'frameworks': ['React'],
            'top_projects': [
                {
                    'project_name': 'Project 1',
                    'score': 95,
                    'primary_language': 'Python',
                    'languages': ['Python'],
                    'frameworks': ['React'],
                    'skills': ['Python', 'React'],
                    'file_count': 25,
                    'lines_of_code': 2500,
                    'duration_days': 30,
                    'intensity': 'High',
                    'collaboration_level': 'Team',
                    'code_quality_score': 85.5,
                    'oop_principles_count': 11,
                    'optimization_count': 2,
                    'has_tests': True,
                    'has_docs': True
                }
            ],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_format_json_success(self, sample_resume):
        """Test successful JSON formatting."""
        result = ResumeFormatter.format_json(sample_resume)
        
        assert result is not None
        assert isinstance(result, str)
        assert '"user_name"' in result
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
        assert parsed['user_name'] == 'test_user'
        assert parsed['total_projects_analyzed'] == 10
    
    def test_format_json_exception_handling(self):
        """Test JSON formatting exception handling."""
        # Create data that will cause json.dumps to fail
        with patch('resume.resume_formatter.json.dumps', side_effect=Exception("JSON error")):
            result = ResumeFormatter.format_json({'test': 'data'})
            assert result is None


class TestResumeFormatterMarkdown:
    """Test Markdown formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'user_name': 'Test User',
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
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.format_markdown(sample_resume)
        
        assert result is not None
        assert '# Test User' in result or '# Your Name' in result
        assert '## Technical Skills' in result
        assert '## Projects' in result
        assert 'Python' in result
        assert 'Project A' in result
    
    def test_format_markdown_contains_sections(self, sample_resume):
        """Test that Markdown contains all required sections."""
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.format_markdown(sample_resume)
        
        # Fixed: Match actual formatter output (## Technical Skills, not ## Skills)
        assert '## Technical Skills' in result
        assert '## Projects' in result
        assert 'Technologies' in result
    
    def test_format_markdown_empty_data(self):
        """Test Markdown formatting with empty data."""
        result = ResumeFormatter.format_markdown(None)
        assert result is None
    
    def test_format_markdown_with_summary_stats(self):
        """Test Markdown formatting with summary stats (stats are no longer displayed)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'summary_stats': {
                'total_lines_of_code': 10000,
                'total_files': 100,
                'unique_languages': 3,
                'unique_frameworks': 2
            },
            'all_skills': ['Python'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        # Summary stats are no longer displayed in the new format
        assert '## Technical Skills' in result
        assert '## Projects' in result
    
    def test_format_markdown_with_categorized_skills(self):
        """Test Markdown formatting with categorized skills."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'categorized_skills': {
                'Languages': ['Python', 'JavaScript'],
                'Frameworks': ['React', 'Django']
            },
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        # Categorized skills now use **Category:** format instead of ###
        assert '**Languages:**' in result
        assert 'Python, JavaScript' in result
        assert '**Frameworks:**' in result
        assert 'React, Django' in result
    
    def test_format_markdown_no_skills(self):
        """Test Markdown formatting with no skills."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': [],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        assert 'No skills identified' in result
    
    def test_format_markdown_with_languages(self):
        """Test Markdown formatting with languages (languages are now in Technical Skills)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'languages': ['Python', 'JavaScript', 'Java'],
            'all_skills': ['Python', 'JavaScript', 'Java'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        # Languages are now included in Technical Skills, not a separate section
        assert '## Technical Skills' in result
        assert 'Python' in result or 'JavaScript' in result
    
    def test_format_markdown_with_frameworks(self):
        """Test Markdown formatting with frameworks (frameworks are now in Technical Skills)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'frameworks': ['React', 'Django', 'Flask'],
            'all_skills': ['React', 'Django', 'Flask'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        # Frameworks are now included in Technical Skills, not a separate section
        assert '## Technical Skills' in result
        assert 'React' in result or 'Django' in result
    
    def test_format_markdown_project_with_all_details(self):
        """Test Markdown formatting with project containing all details."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': [],
            'top_projects': [{
                'project_name': 'test-project',
                'primary_language': 'Python',
                'first_file': '2024-01-01',
                'last_file': '2024-01-31',
                'frameworks': ['Django', 'React'],
                'collaboration_level': 'Team',
                'summary': 'This is a test project description that shows what the project does.',
                'skills': ['Python', 'Django', 'React']
            }],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_markdown(resume_data)
        assert result is not None
        # New format shows project name, dates, description, and technologies
        assert '### test-project' in result
        assert '**Technologies:**' in result
        assert 'Python' in result or 'Django' in result
        # Technical details like scale, score, etc. are no longer shown
    
    def test_format_markdown_exception_handling(self):
        """Test Markdown formatting exception handling."""
        # Create data that will cause an exception when trying to format
        # We'll mock the join operation to raise an exception
        with patch('builtins.print'):  # Suppress print output
            # Create a resume data with an object that can't be converted to string
            class BadObject:
                def __str__(self):
                    raise Exception("Cannot convert to string")
            
            resume_data = {
                'user_name': 'Test User',
                'total_projects_analyzed': 5,
                'top_projects_displayed': 2,
                'all_skills': [BadObject()],  # This will cause an exception
                'top_projects': [],
                'generated_at': '2024-01-01T10:00:00'
            }
            
            result = ResumeFormatter.format_markdown(resume_data)
            # The exception should be caught and None returned
            assert result is None


class TestResumeFormatterText:
    """Test plain text formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'user_name': 'Test User',
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
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.format_text(sample_resume)
        
        assert result is not None
        # New format uses user name instead of "RESUME"
        assert 'TEST USER' in result or 'Test User' in result
        assert 'TECHNICAL SKILLS' in result
        assert 'PROJECTS' in result
    
    
    def test_format_text_empty_data(self):
        """Test text formatting with empty data."""
        result = ResumeFormatter.format_text(None)
        assert result is None
    
    def test_format_text_with_summary_stats(self):
        """Test text formatting with summary stats (stats are no longer displayed)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'summary_stats': {
                'total_lines_of_code': 15000,
                'total_files': 150,
                'unique_languages': 4,
                'unique_frameworks': 3
            },
            'all_skills': [],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_text(resume_data)
        assert result is not None
        # Summary stats are no longer displayed in the new format
        assert 'TECHNICAL SKILLS' in result
        assert 'PROJECTS' in result
    
    def test_format_text_with_categorized_skills(self):
        """Test text formatting with categorized skills."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'categorized_skills': {
                'Backend': ['Python', 'Django'],
                'Frontend': ['React', 'TypeScript']
            },
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_text(resume_data)
        assert result is not None
        # Categorized skills now use "Category: skills" format instead of bullet points
        assert 'Backend:' in result
        assert 'Python' in result
        assert 'Django' in result
        assert 'Frontend:' in result
        assert 'React' in result
        assert 'TypeScript' in result
    
    def test_format_text_no_skills(self):
        """Test text formatting with no skills."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': [],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_text(resume_data)
        assert result is not None
        # Format changed - check for "No skills identified" without indentation
        assert 'No skills identified' in result
    
    def test_format_text_with_languages(self):
        """Test text formatting with languages (languages are now in Technical Skills)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'languages': ['Python', 'Java', 'C++'],
            'all_skills': ['Python', 'Java', 'C++'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_text(resume_data)
        assert result is not None
        # Languages are now included in Technical Skills, not a separate section
        assert 'TECHNICAL SKILLS' in result
        assert 'Python' in result
    
    def test_format_text_with_frameworks(self):
        """Test text formatting with frameworks (frameworks are now in Technical Skills)."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'frameworks': ['Django', 'Flask', 'FastAPI'],
            'all_skills': ['Django', 'Flask', 'FastAPI'],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        result = ResumeFormatter.format_text(resume_data)
        assert result is not None
        # Frameworks are now included in Technical Skills, not a separate section
        assert 'TECHNICAL SKILLS' in result
        assert 'Django' in result
    
    def test_format_text_exception_handling(self):
        """Test text formatting exception handling."""
        with patch('builtins.print'):  # Suppress print output
            # Create a resume data with an object that can't be converted to string
            class BadObject:
                def __str__(self):
                    raise Exception("Cannot convert to string")
            
            resume_data = {
                'user_name': 'Test User',
                'total_projects_analyzed': 5,
                'top_projects_displayed': 2,
                'all_skills': [BadObject()],  # This will cause an exception
                'top_projects': [],
                'generated_at': '2024-01-01T10:00:00'
            }
            
            result = ResumeFormatter.format_text(resume_data)
            # The exception should be caught and None returned
            assert result is None


class TestResumeFormatterInterface:
    """Test main formatter interface."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for testing."""
        return {
            'user_name': 'Test User',
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
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'markdown')
        
        assert result is not None
        # New format uses user name instead of "# Resume"
        assert '# Test User' in result or '# Your Name' in result
    
    def test_get_formatted_resume_text(self, sample_resume):
        """Test getting resume in text format."""
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'text')
        
        assert result is not None
        # New format uses user name instead of "RESUME"
        assert 'TEST USER' in result or 'Test User' in result
    
    def test_get_formatted_resume_default_format(self, sample_resume):
        """Test default format is text."""
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.get_formatted_resume(sample_resume)
        
        assert result is not None
        # New format uses user name instead of "RESUME"
        assert 'TEST USER' in result or 'Test User' in result
    
    def test_get_formatted_resume_invalid_format(self, sample_resume):
        """Test invalid format defaults to text."""
        # Add user_name to sample_resume
        sample_resume['user_name'] = 'Test User'
        result = ResumeFormatter.get_formatted_resume(sample_resume, 'invalid')
        
        assert result is not None
        # New format uses user name instead of "RESUME"
        assert 'TEST USER' in result or 'Test User' in result
    
    def test_get_formatted_resume_empty_data(self):
        """Test get_formatted_resume with empty data."""
        result = ResumeFormatter.get_formatted_resume(None, 'text')
        assert result is None


class TestResumeFormatterPDF:
    """Test PDF formatting functionality."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume data for PDF testing."""
        return {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': ['Python', 'JavaScript', 'React', 'Docker'],
            'categorized_skills': {
                'Languages': ['Python', 'JavaScript'],
                'Frameworks': ['React', 'Docker']
            },
            'languages': ['Python', 'JavaScript'],
            'frameworks': ['React', 'Docker', 'Node.js'],
            'top_projects': [
                {
                    'project_name': 'Web App',
                    'project_id': 1,
                    'primary_language': 'Python',
                    'languages': ['Python', 'JavaScript'],
                    'frameworks': ['React', 'Docker'],
                    'skills': ['Python', 'JavaScript', 'React'],
                    'first_file': '2024-01-01',
                    'last_file': '2024-01-31',
                    'intensity': 'High',
                    'collaboration_level': 'Team',
                    'summary': 'A web application project description.'
                }
            ],
            'generated_at': '2024-01-01T10:00:00'
        }
    
    def test_format_pdf_success(self, sample_resume):
        """Test successful PDF generation."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = ResumeFormatter.format_pdf(sample_resume, output_path)
            
            assert result == True
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_format_pdf_creates_valid_file(self, sample_resume):
        """Test that generated PDF is a valid PDF file."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = ResumeFormatter.format_pdf(sample_resume, output_path)
            
            assert result == True
            
            # Check PDF magic bytes
            with open(output_path, 'rb') as f:
                header = f.read(4)
                assert header == b'%PDF'
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_format_pdf_empty_projects(self):
        """Test PDF generation with no projects."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 0,
            'top_projects_displayed': 0,
            'all_skills': [],
            'categorized_skills': {},
            'languages': [],
            'frameworks': [],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = ResumeFormatter.format_pdf(resume_data, output_path)
            
            assert result == True
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_format_pdf_invalid_path(self, sample_resume):
        """Test PDF generation with invalid output path."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        # Use an invalid path that cannot be written to
        invalid_path = '/nonexistent_directory/resume.pdf'
        
        result = ResumeFormatter.format_pdf(sample_resume, invalid_path)
        
        assert result == False
    
    def test_format_pdf_empty_data(self):
        """Test PDF generation with empty data."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = ResumeFormatter.format_pdf(None, output_path)
            assert result == False
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_format_pdf_no_skills(self):
        """Test PDF generation with no skills."""
        try:
            import reportlab
        except ImportError:
            pytest.skip("reportlab not installed")
        
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': [],
            'categorized_skills': {},
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = ResumeFormatter.format_pdf(resume_data, output_path)
            assert result == True
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_format_pdf_import_error(self):
        """Test PDF generation when reportlab is not available."""
        resume_data = {
            'user_name': 'Test User',
            'total_projects_analyzed': 5,
            'top_projects_displayed': 2,
            'all_skills': [],
            'top_projects': [],
            'generated_at': '2024-01-01T10:00:00'
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            # Mock ImportError
            with patch('builtins.__import__', side_effect=ImportError("No module named 'reportlab'")):
                with patch('builtins.print'):  # Suppress print output
                    result = ResumeFormatter.format_pdf(resume_data, output_path)
                    assert result == False
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])