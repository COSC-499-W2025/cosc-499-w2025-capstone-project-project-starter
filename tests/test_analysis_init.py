"""
Tests for analysis/__init__.py lazy import functions
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add src directory to Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis import (
    rank_all_projects,
    display_rankings,
    calculate_project_score,
    rank_local_project
)


class TestAnalysisInit:
    """Test lazy import functions in analysis/__init__.py"""
    
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_all_projects(self, mock_rank_all):
        """Test that rank_all_projects imports and calls project_ranking.rank_all_projects"""
        mock_rank_all.return_value = [{"project_id": 1, "filename": "test.zip", "score": 85.5}]
        
        result = rank_all_projects()
        
        mock_rank_all.assert_called_once()
        assert result == [{"project_id": 1, "filename": "test.zip", "score": 85.5}]
    
    @patch('analysis.project_ranking.display_rankings')
    def test_display_rankings(self, mock_display):
        """Test that display_rankings imports and calls project_ranking.display_rankings"""
        ranked_projects = [{"project_id": 1, "filename": "test.zip", "score": 85.5}]
        
        display_rankings(ranked_projects)
        
        mock_display.assert_called_once_with(ranked_projects)
    
    @patch('analysis.project_ranking.calculate_project_score')
    def test_calculate_project_score(self, mock_calculate):
        """Test that calculate_project_score imports and calls project_ranking.calculate_project_score"""
        mock_calculate.return_value = 85.5
        analysis_data = {"by_activity": {"code": {"count": 10, "bytes": 5000}}}
        
        result = calculate_project_score(analysis_data)
        
        mock_calculate.assert_called_once_with(analysis_data)
        assert result == 85.5
    
    @patch('analysis.project_ranking.rank_local_project')
    def test_rank_local_project(self, mock_rank_local):
        """Test that rank_local_project imports and calls project_ranking.rank_local_project"""
        mock_rank_local.side_effect = NotImplementedError("Local ranking disabled")
        project_path = "/path/to/project"
        
        with pytest.raises(NotImplementedError):
            rank_local_project(project_path)
        
        mock_rank_local.assert_called_once_with(project_path)

