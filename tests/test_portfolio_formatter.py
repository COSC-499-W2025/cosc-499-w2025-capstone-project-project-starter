# tests/test_portfolio_formatter.py
import sys
import os
import pytest
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_formatter import PortfolioFormatter
from src.common.schemas import PortfolioCardResponse, TechStack


class TestPortfolioFormatter:
    """Test suite for PortfolioFormatter functionality"""
    
    def setup_method(self):
        self.sample_data = {
            'summary': {'total_projects': 2, 'total_files': 30, 'total_lines_of_code': 8000, 'total_size_mb': 4.0},
            'skills': {
                'categorized': {'Programming Languages': ['Python']},
                'languages': ['Python'],
                'frameworks': ['Flask']
            },
            'projects': [{
                'name': 'project1.zip',
                'primary_language': 'Python',
                'languages': ['Python'],
                'file_count': 20,
                'lines_of_code': 5000,
                'skills': ['Python', 'Flask'],
                'summary': 'Test project',
                'frameworks': ['Flask'],
                'has_tests': True,
                'has_docs': True,
                'code_quality_score': 85,
                'collaboration_analysis': ''
            }]
        }
    
    def test_format_text_success(self):
        """Test successful text formatting"""
        result = PortfolioFormatter.format_text(self.sample_data)
        assert result is not None
        assert 'PORTFOLIO OVERVIEW' in result
        assert 'TECHNICAL EXPERTISE' in result
        assert 'FEATURED PROJECTS' in result
        assert 'Python' in result
    
    def test_format_text_with_error(self):
        """Test text formatting with error"""
        result = PortfolioFormatter.format_text({'error': 'Test error'})
        assert 'ERROR' in result
        assert 'Test error' in result
    
    def test_format_markdown_success(self):
        """Test successful markdown formatting"""
        result = PortfolioFormatter.format_markdown(self.sample_data)
        assert result is not None
        assert '# Portfolio' in result
        assert '## Technical Expertise' in result
        assert 'Python' in result
    
    def test_format_markdown_with_error(self):
        """Test markdown formatting with error"""
        result = PortfolioFormatter.format_markdown({'error': 'Test error'})
        assert '# ERROR' in result
    
    def test_get_formatted_portfolio_text(self):
        """Test get_formatted_portfolio with text format"""
        result = PortfolioFormatter.get_formatted_portfolio(self.sample_data, 'text')
        assert result is not None
        assert 'PORTFOLIO OVERVIEW' in result
    
    def test_get_formatted_portfolio_markdown(self):
        """Test get_formatted_portfolio with markdown format"""
        result = PortfolioFormatter.get_formatted_portfolio(self.sample_data, 'markdown')
        assert result is not None
        assert '# Portfolio' in result
    
    def test_get_formatted_portfolio_unknown_format(self):
        """Test get_formatted_portfolio with unknown format falls back to text"""
        result = PortfolioFormatter.get_formatted_portfolio(self.sample_data, 'unknown')
        assert result is not None
        assert 'PORTFOLIO OVERVIEW' in result
    
    def test_format_text_with_none(self):
        """Test text formatting with None (should not raise AttributeError)"""
        result = PortfolioFormatter.format_text(None)
        assert result is not None
        assert 'ERROR' in result
        assert 'Invalid portfolio data' in result
    
    def test_format_text_with_non_dict(self):
        """Test text formatting with non-dict value (should not raise TypeError)"""
        # Test with various non-dict types
        for invalid_data in [1, "string", [], True, False, 0]:
            result = PortfolioFormatter.format_text(invalid_data)
            assert result is not None
            assert 'ERROR' in result
            assert 'Invalid portfolio data' in result
    
    def test_format_markdown_with_none(self):
        """Test markdown formatting with None (should not raise AttributeError)"""
        result = PortfolioFormatter.format_markdown(None)
        assert result is not None
        assert '# ERROR' in result
        assert 'Invalid portfolio data' in result
    
    def test_format_markdown_with_non_dict(self):
        """Test markdown formatting with non-dict value (should not raise TypeError)"""
        # Test with various non-dict types
        for invalid_data in [1, "string", [], True, False, 0]:
            result = PortfolioFormatter.format_markdown(invalid_data)
            assert result is not None
            assert '# ERROR' in result
            assert 'Invalid portfolio data' in result

@pytest.fixture
def mock_single_project_data():
    """
    Simulates the output of ProjectAnalyzer for a SINGLE project.
    """
    return {
        'project_info': {
            'filename': 'crypto-trading-bot-main.zip',
            'id': 101,
            'created_at': '2025-01-20T10:00:00'
        },
        'languages': {
            'primary_language': 'Python',
            'detected_languages': ['Python', 'SQL', 'Docker']
        },
        'frameworks': ['FastAPI', 'Pandas'], # Can be list or dict
        'file_statistics': {
            'total_lines_of_code': 1500,
            'total_files': 25
        },
        'project_structure': {
            'has_tests': True,
            'has_docs': True
        },
        'collaboration_analysis': {
            'contributors': ['Kevin', 'Sami', 'Evan']
        }
    }


def test_format_project_card_structure(mock_single_project_data):
    """
    Verify that the raw data is correctly mapped to the Pydantic Schema.
    """
    card = PortfolioFormatter.format_project_card(mock_single_project_data)
    
    # 1. Check Schema Compliance
    assert isinstance(card, PortfolioCardResponse)
    
    # 2. Check Title Cleaning
    assert card.title == "Crypto Trading Bot"
    assert card.project_id == "proj_101"
    
    # 3. Check Descriptions
    assert "1500+ lines" in card.short_description
    assert "Python" in card.full_description

def test_format_project_card_tech_stack(mock_single_project_data):
    """
    Verify that languages and frameworks are converted to TechStack objects.
    """
    card = PortfolioFormatter.format_project_card(mock_single_project_data)
    
    # Extract names for easy checking
    tech_names = [t.name for t in card.technologies]
    
    assert "Python" in tech_names
    assert "FastAPI" in tech_names
    assert "Docker" in tech_names
    
    # Verify categories
    for tech in card.technologies:
        if tech.name == "Python":
            assert tech.category == "Language"
        if tech.name == "FastAPI":
            assert tech.category == "Framework"

def test_format_project_card_success_metrics(mock_single_project_data):
    """
    Verify 'Evidence of Success' is generated from static metrics.
    """
    card = PortfolioFormatter.format_project_card(mock_single_project_data)
    
    # Based on our mock data (1500 LOC, Has Tests, Has Docs)
    assert "Large Scale Architecture" in card.success_metrics
    assert "Verified Reliability (Unit Tests)" in card.success_metrics
    assert "Well Documented" in card.success_metrics

def test_format_project_card_collaborators(mock_single_project_data):
    """
    Verify contributors are correctly extracted.
    """
    card = PortfolioFormatter.format_project_card(mock_single_project_data)
    
    assert len(card.collaborators) == 3
    assert "Kevin" in card.collaborators
    assert "Sami" in card.collaborators

def test_format_project_card_missing_data():
    """
    Verify resilience: formatting should not crash even if data is empty.
    """
    empty_data = {'project_info': {}}
    
    card = PortfolioFormatter.format_project_card(empty_data)
    
    assert card.title == "Untitled Project"
    assert card.technologies == []
    assert card.success_metrics == []
    assert card.collaborators == []
    # Ensure description has safe defaults
    assert "0 modules" in card.short_description

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

