# tests/test_portfolio_display.py
import sys
import os
import pytest
from unittest.mock import patch, Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_display import display_portfolio, portfolio_menu


class TestPortfolioDisplay:
    """Test suite for portfolio display functionality"""
    
    @patch('portfolio.portfolio_display.PortfolioFormatter')
    @patch('portfolio.portfolio_display.PortfolioManager')
    def test_display_portfolio_success(self, mock_manager_class, mock_formatter_class):
        """Test successful portfolio display"""
        mock_manager = Mock()
        mock_manager.generate_portfolio_report.return_value = {
            'summary': {'total_projects': 1},
            'skills': {},
            'projects': []
        }
        mock_manager_class.return_value = mock_manager
        
        mock_formatter = Mock()
        mock_formatter.get_formatted_portfolio.return_value = "Formatted portfolio"
        mock_formatter_class.return_value = mock_formatter
        
        display_portfolio('test_user', 'text')
        
        mock_manager.generate_portfolio_report.assert_called_once()
        mock_formatter.get_formatted_portfolio.assert_called_once()
    
    @patch('portfolio.portfolio_display.PortfolioManager')
    def test_display_portfolio_with_error(self, mock_manager_class):
        """Test portfolio display with error"""
        mock_manager = Mock()
        mock_manager.generate_portfolio_report.return_value = {'error': 'Test error'}
        mock_manager_class.return_value = mock_manager
        
        # Should not raise exception
        display_portfolio('test_user')
        mock_manager.generate_portfolio_report.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

