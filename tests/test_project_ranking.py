"""
Tests for project ranking functionality
"""
import sys
import os
import pytest
from unittest.mock import patch, call
from datetime import datetime

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from analysis.project_ranking import (
    calculate_project_score,
    display_rankings,
    rank_and_summarize_top_projects,
    rank_all_projects
)


def test_calculate_score_key_metrics():
    """Test scoring with key_metrics analysis data"""
    analysis_data = {
        "by_activity": {
            "code": {"score": 100.0},
            "doc": {"score": 50.0},
            "data": {"score": 30.0}
        },
        "totals": {"files": 10, "lines": 500},
        "by_language": [
            {"language": "Python"},
            {"language": "JavaScript"}
        ]
    }
    
    score = calculate_project_score(analysis_data)
    assert score > 0
    assert isinstance(score, float)


def test_score_increases_with_tests():
    """Test that projects with tests score higher"""
    without_tests = {
        "structure": {"has_tests": False, "has_docs": False, "has_config": False},
        "metrics": {"total_lines_of_code": 100},
        "skills": [],
        "frameworks": []
    }
    
    with_tests = {
        "structure": {"has_tests": True, "has_docs": False, "has_config": False},
        "metrics": {"total_lines_of_code": 100},
        "skills": [],
        "frameworks": []
    }
    
    score_without = calculate_project_score(without_tests)
    score_with = calculate_project_score(with_tests)
    
    assert score_with > score_without


class TestDisplayRankings:
    def test_display_rankings_empty_list(self):
        display_rankings([])
    
    def test_display_rankings_with_projects(self):
        ranked_projects = [
            {
                "project_id": 1,
                "filename": "project1.zip",
                "score": 150.5,
                "created_at": datetime(2024, 1, 1)
            },
            {
                "project_id": 2,
                "filename": "project2.zip",
                "score": 120.3,
                "created_at": datetime(2024, 1, 2)
            }
        ]
        
        # Should process without error
        display_rankings(ranked_projects)


class TestRankAndSummarizeTopProjects:

    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_top_projects_success(self, mock_rank_all, mock_summarize):
        mock_ranked = [
            {
                "project_id": 1,
                "filename": "top_project.zip",
                "score": 200.0,
                "created_at": datetime(2024, 1, 1),
                "analysis": {}
            },
            {
                "project_id": 2,
                "filename": "second_project.zip",
                "score": 150.0,
                "created_at": datetime(2024, 1, 2),
                "analysis": {}
            },
            {
                "project_id": 3,
                "filename": "third_project.zip",
                "score": 100.0,
                "created_at": datetime(2024, 1, 3),
                "analysis": {}
            }
        ]
        mock_rank_all.return_value = mock_ranked
        mock_summarize.return_value = "Summary text"
        
        rank_and_summarize_top_projects()
        
        # Verify rank_all_projects was called
        mock_rank_all.assert_called_once()
        
        # Verify summarize_project was called 3 times (for top 3)
        assert mock_summarize.call_count == 3
        assert mock_summarize.call_args_list[0] == call(1)
        assert mock_summarize.call_args_list[1] == call(2)
        assert mock_summarize.call_args_list[2] == call(3)
    
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_no_projects(self, mock_rank_all):
        mock_rank_all.return_value = []
        
        # Should not raise an exception
        rank_and_summarize_top_projects()
        
        mock_rank_all.assert_called_once()
    
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_less_than_3_projects(self, mock_rank_all, mock_summarize):
        mock_ranked = [
            {
                "project_id": 1,
                "filename": "only_project.zip",
                "score": 100.0,
                "created_at": datetime(2024, 1, 1),
                "analysis": {}
            }
        ]
        mock_rank_all.return_value = mock_ranked
        mock_summarize.return_value = "Summary text"
        
        rank_and_summarize_top_projects()
        
        # Should only summarize 1 project (min of 3 and actual count)
        assert mock_summarize.call_count == 1
        assert mock_summarize.call_args_list[0] == call(1)
    
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    
    def test_rank_and_summarize_more_than_3_projects(self, mock_rank_all, mock_summarize):
        mock_ranked = [
            {"project_id": 1, "filename": "p1.zip", "score": 100.0, "created_at": datetime(2024, 1, 1), "analysis": {}},
            {"project_id": 2, "filename": "p2.zip", "score": 90.0, "created_at": datetime(2024, 1, 2), "analysis": {}},
            {"project_id": 3, "filename": "p3.zip", "score": 80.0, "created_at": datetime(2024, 1, 3), "analysis": {}},
            {"project_id": 4, "filename": "p4.zip", "score": 70.0, "created_at": datetime(2024, 1, 4), "analysis": {}},
            {"project_id": 5, "filename": "p5.zip", "score": 60.0, "created_at": datetime(2024, 1, 5), "analysis": {}}
        ]
        mock_rank_all.return_value = mock_ranked
        mock_summarize.return_value = "Summary text"
        
        rank_and_summarize_top_projects()
        
        # Should only summarize top 3, not all 5
        assert mock_summarize.call_count == 3
        assert mock_summarize.call_args_list[0] == call(1)
        assert mock_summarize.call_args_list[1] == call(2)
        assert mock_summarize.call_args_list[2] == call(3)
        # Verify project 4 and 5 were NOT summarized
        assert call(4) not in mock_summarize.call_args_list
        assert call(5) not in mock_summarize.call_args_list
    
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_summary_error_handling(self, mock_rank_all, mock_summarize):
        mock_ranked = [
            {
                "project_id": 1,
                "filename": "project.zip",
                "score": 100.0,
                "created_at": datetime(2024, 1, 1),
                "analysis": {}
            }
        ]
        mock_rank_all.return_value = mock_ranked
        mock_summarize.side_effect = Exception("Summary error")

        rank_and_summarize_top_projects()

        mock_rank_all.assert_called_once()
        mock_summarize.assert_called_once_with(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

