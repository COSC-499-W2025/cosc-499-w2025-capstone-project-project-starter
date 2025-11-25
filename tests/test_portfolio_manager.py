# tests/test_portfolio_manager.py
import sys
import os
import pytest
from unittest.mock import Mock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_manager import PortfolioManager


class TestPortfolioManager:
    """Test suite for PortfolioManager functionality"""
    
    def setup_method(self):
        self.user_id = 'test_user'
        self.manager = PortfolioManager(self.user_id)
    
    @patch('portfolio.portfolio_manager.rank_all_projects')
    def test_generate_portfolio_report_no_projects(self, mock_rank_all):
        """Test portfolio generation when no projects exist"""
        mock_rank_all.return_value = []
        result = self.manager.generate_portfolio_report()
        assert 'error' in result
        assert result['error'] == 'No projects found'
        assert 'timestamp' in result
    
    @patch('portfolio.portfolio_manager.rank_all_projects')
    def test_generate_portfolio_report_exception_handling(self, mock_rank_all):
        """Test exception handling in portfolio generation"""
        mock_rank_all.side_effect = Exception("Database error")
        result = self.manager.generate_portfolio_report()
        assert 'error' in result
        assert 'timestamp' in result
    
    def test_generate_project_summary_text_basic(self):
        """Test project summary text generation"""
        summary = {
            'project_info': {'filename': 'test.zip'},
            'languages': {'primary_language': 'Python', 'languages': ['Python']}
        }
        result = self.manager._generate_project_summary_text(
            summary, {}, {'totals': {'files': 10, 'lines': 1000}}, []
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert 'Python' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

