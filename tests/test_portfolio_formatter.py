import sys
import os
import pytest
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from portfolio.portfolio_formatter import PortfolioFormatter
from src.common.schemas import PortfolioCardResponse, TechStack

class TestPortfolioFormatter:
    """Test suite for PortfolioFormatter functionality"""
    
    # setup_method DELETED (Handled by conftest.py)

    def test_format_project_card(self, mock_project_data):
        """Test formatting a complete project data dictionary."""
        # Uses shared data automatically
        card = PortfolioFormatter.format_project_card(mock_project_data)
        
        # Verify basic fields
        assert isinstance(card, PortfolioCardResponse)
        assert card.title == "Stock Trader V2"
        assert card.short_description is not None
        
        # Verify tech stack
        tech_names = [t.name for t in card.technologies]
        assert "Python" in tech_names
        assert "FastAPI" in tech_names
        
    def test_format_project_card_with_missing_fields(self, mock_project_data):
        """Test formatting when optional fields are missing."""
        incomplete_data = mock_project_data.copy()
        incomplete_data['frameworks'] = []
        incomplete_data['code_quality_score'] = None
        
        card = PortfolioFormatter.format_project_card(incomplete_data)
        
        assert card.title == "Stock Trader V2"
        # Should handle missing score gracefully
        assert any("Quality" not in m for m in card.success_metrics)
        
    def test_format_tech_stack(self, mock_project_data):
        """Test technology stack formatting."""
        card = PortfolioFormatter.format_project_card(mock_project_data)
        
        tech_names = [t.name for t in card.technologies]
        assert "Python" in tech_names
        assert "FastAPI" in tech_names
        
        fastapi = next(t for t in card.technologies if t.name == "FastAPI")
        assert fastapi.category == "Framework"

    def test_portfolio_custom_overrides(self, mock_project_data):
        """Test that the formatter respects user_options."""
        user_prefs = {
            "custom_title": "My Best Work",
            "custom_description": "A custom description written by the user.",
            "custom_role": "Architect"
        }
        
        card = PortfolioFormatter.format_project_card(mock_project_data, user_options=user_prefs)
        
        assert card.title == "My Best Work"
        assert card.full_description == "A custom description written by the user."
        assert card.my_role == "Architect"
        assert "Python" in [t.name for t in card.technologies]

    def test_missing_data_resilience(self):
        """Verify formatting works even with empty data."""
        empty_data = {'project_info': {}}
        card = PortfolioFormatter.format_project_card(empty_data)
        assert card.title == "Untitled Project"
        assert card.technologies == []