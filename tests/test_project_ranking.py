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
            "code": {"count": 10, "bytes": 5000},
            "doc": {"count": 5, "bytes": 2000},
            "data": {"count": 3, "bytes": 1000}
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

    @patch('analysis.project_ranking.get_stored_ranking_by_project_id')
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_top_projects_success(self, mock_rank_all, mock_summarize, mock_get_stored):
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
        # Mock get_stored_ranking_by_project_id to return None (no stored summaries)
        mock_get_stored.return_value = None
        
        rank_and_summarize_top_projects()
        
        # Verify rank_all_projects was called
        mock_rank_all.assert_called_once()
        
        # Verify get_stored_ranking_by_project_id was called for each project
        assert mock_get_stored.call_count == 3
        
        # Verify summarize_project was called 3 times (for top 3, since no stored summaries)
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
    
    @patch('analysis.project_ranking.get_stored_ranking_by_project_id')
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_less_than_3_projects(self, mock_rank_all, mock_summarize, mock_get_stored):
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
        # Mock get_stored_ranking_by_project_id to return None (no stored summaries)
        mock_get_stored.return_value = None
        
        rank_and_summarize_top_projects()
        
        # Should only summarize 1 project (min of 3 and actual count)
        assert mock_summarize.call_count == 1
        assert mock_summarize.call_args_list[0] == call(1)
        # Verify get_stored_ranking_by_project_id was called
        assert mock_get_stored.call_count == 1
    
    @patch('analysis.project_ranking.get_stored_ranking_by_project_id')
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_more_than_3_projects(self, mock_rank_all, mock_summarize, mock_get_stored):
        mock_ranked = [
            {"project_id": 1, "filename": "p1.zip", "score": 100.0, "created_at": datetime(2024, 1, 1), "analysis": {}},
            {"project_id": 2, "filename": "p2.zip", "score": 90.0, "created_at": datetime(2024, 1, 2), "analysis": {}},
            {"project_id": 3, "filename": "p3.zip", "score": 80.0, "created_at": datetime(2024, 1, 3), "analysis": {}},
            {"project_id": 4, "filename": "p4.zip", "score": 70.0, "created_at": datetime(2024, 1, 4), "analysis": {}},
            {"project_id": 5, "filename": "p5.zip", "score": 60.0, "created_at": datetime(2024, 1, 5), "analysis": {}}
        ]
        mock_rank_all.return_value = mock_ranked
        mock_summarize.return_value = "Summary text"
        # Mock get_stored_ranking_by_project_id to return None (no stored summaries)
        mock_get_stored.return_value = None
        
        rank_and_summarize_top_projects()
        
        # Should only summarize top 3, not all 5
        assert mock_summarize.call_count == 3
        assert mock_summarize.call_args_list[0] == call(1)
        assert mock_summarize.call_args_list[1] == call(2)
        assert mock_summarize.call_args_list[2] == call(3)
        # Verify project 4 and 5 were NOT summarized
        assert call(4) not in mock_summarize.call_args_list
        assert call(5) not in mock_summarize.call_args_list
        # Verify get_stored_ranking_by_project_id was called 3 times (for top 3)
        assert mock_get_stored.call_count == 3
    
    @patch('analysis.project_ranking.get_stored_ranking_by_project_id')
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_summary_error_handling(self, mock_rank_all, mock_summarize, mock_get_stored):
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
        # Mock get_stored_ranking_by_project_id to return None (no stored summaries)
        mock_get_stored.return_value = None

        rank_and_summarize_top_projects()

        mock_rank_all.assert_called_once()
        mock_get_stored.assert_called_once_with(1)
        mock_summarize.assert_called_once_with(1)
    
    @patch('analysis.project_ranking.get_stored_ranking_by_project_id')
    @patch('analysis.project_ranking.summarize_project')
    @patch('analysis.project_ranking.rank_all_projects')
    def test_rank_and_summarize_uses_stored_summary(self, mock_rank_all, mock_summarize, mock_get_stored):
        """Test that stored summaries are used when available"""
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
        
        # Mock stored ranking with a summary
        mock_get_stored.return_value = {
            "project_id": 1,
            "summary": "This is a stored summary"
        }
        
        rank_and_summarize_top_projects()
        
        # Verify get_stored_ranking_by_project_id was called
        mock_get_stored.assert_called_once_with(1)
        # Verify summarize_project was NOT called (stored summary used instead)
        mock_summarize.assert_not_called()


class TestRankingStorage:
    """Tests for ranking storage functionality - all database operations are mocked"""
    
    @patch('analysis.ranking_storage.init_ranking_storage_table')
    @patch('analysis.ranking_storage.with_db_cursor')
    def test_save_rankings_to_database(self, mock_cursor, mock_init):
        """Test that rankings can be saved to the database (mocked, no DB changes)"""
        from analysis.ranking_storage import save_rankings_to_db
        
        # Mock database cursor context manager
        mock_cursor_obj = mock_cursor.return_value.__enter__.return_value
        mock_cursor_obj.fetchall.return_value = []  # No existing rankings
        
        ranked_projects = [
            {
                "project_id": 1,
                "filename": "project1.zip",
                "score": 150.5,
                "created_at": datetime(2024, 1, 1),
                "analysis": {}
            },
            {
                "project_id": 2,
                "filename": "project2.zip",
                "score": 120.3,
                "created_at": datetime(2024, 1, 2),
                "analysis": {}
            }
        ]
        
        summaries = {1: "Summary for project 1", 2: "Summary for project 2"}
        
        result = save_rankings_to_db(ranked_projects, summaries)
        
        # Verify save was attempted (but no actual DB changes)
        assert result is True
        # Verify init was called
        mock_init.assert_called_once()
        # Verify DELETE was called to clear existing rankings
        delete_calls = [str(call) for call in mock_cursor_obj.execute.call_args_list if "DELETE" in str(call[0])]
        assert len(delete_calls) > 0
        # Verify INSERT was called for each project
        insert_calls = [str(call) for call in mock_cursor_obj.execute.call_args_list if "INSERT" in str(call[0])]
        assert len(insert_calls) == 2
    
    @patch('analysis.project_ranking.get_stored_rankings')
    @patch('analysis.project_ranking.analyze_project_from_db')
    @patch('analysis.project_ranking.get_connection')
    def test_rank_all_projects_uses_stored_scores(self, mock_conn, mock_analyze, mock_get_stored):
        """Test that stored scores are used when available (mocked, no DB changes)"""
        # Mock stored rankings with edited scores
        mock_get_stored.return_value = [
            {
                "project_id": 1,
                "score": 999.99,  # Edited score (different from calculated)
                "rank_position": 1
            }
        ]
        
        # Mock database connection with nested context manager pattern
        # The code uses: with get_connection() as conn, conn.cursor() as cur:
        mock_connection = mock_conn.return_value.__enter__.return_value
        mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
        mock_cursor.execute.return_value = None
        mock_cursor.fetchall.return_value = [
            (1, "project1.zip", datetime(2024, 1, 1))
        ]
        
        # Mock analysis (should still be called for analysis data)
        mock_analyze.return_value = {
            "by_activity": {"code": {"count": 10, "bytes": 1000}},
            "totals": {"lines": 500},
            "by_language": []
        }
        
        ranked = rank_all_projects()
        
        # Verify stored score was used
        assert len(ranked) == 1
        assert ranked[0]["score"] == 999.99  # Should use stored score, not calculated
        # Verify analysis was still called (needed for other data)
        mock_analyze.assert_called_once_with(1, silent=True)
        # Verify get_stored_rankings was called to check for stored scores
        mock_get_stored.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

