# tests/test_portfolio_formatter.py
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_formatter import PortfolioFormatter


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

