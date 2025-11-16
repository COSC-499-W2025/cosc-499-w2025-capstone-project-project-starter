import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.resume_manager import ResumeManager


class TestResumeTableInitialization:
    """Test database table creation."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_init_resume_table_success(self, mock_with_db_cursor):
        """Test successful initialization of resume table."""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        result = ResumeManager.init_resume_table()
        
        assert result == True
        assert mock_cursor.execute.call_count == 2
        assert mock_with_db_cursor.called
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_init_resume_table_failure(self, mock_with_db_cursor):
        """Test handling of table initialization failure."""
        mock_with_db_cursor.side_effect = Exception("Database error")
        
        result = ResumeManager.init_resume_table()
        
        assert result == False


class TestUserResumeStorage:
    """Test user resume storage and retrieval."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_store_user_resume_success(self, mock_with_db_cursor):
        """Test successful storage of user resume."""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        user_id = "test_user"
        resume_data = {
            'total_projects_analyzed': 10,
            'top_projects_displayed': 5,
            'all_skills': ['Python', 'JavaScript']
        }
        
        result = ResumeManager.store_user_resume(user_id, resume_data)
        
        assert result == True
        mock_cursor.execute.assert_called_once()
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_user_resume_success(self, mock_with_db_cursor):
        """Test successful retrieval of user resume."""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        resume_data = '{"total_projects_analyzed": 10, "all_skills": ["Python"]}'
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        updated_at = datetime(2024, 1, 1, 11, 0, 0)
        mock_cursor.fetchone.return_value = (resume_data, created_at, updated_at)
        
        result = ResumeManager.get_user_resume("test_user")
        
        assert result is not None
        assert result['resume_data'] == resume_data
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_user_resume_not_found(self, mock_with_db_cursor):
        """Test retrieval when user resume does not exist."""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        mock_cursor.fetchone.return_value = None
        
        result = ResumeManager.get_user_resume("nonexistent_user")
        
        assert result is None


class TestResumeOperations:
    """Test resume helper operations."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_delete_user_resume_success(self, mock_with_db_cursor):
        """Test successful deletion of user resume."""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        result = ResumeManager.delete_user_resume("test_user")
        
        assert result == True
    
    @patch('resume.resume_manager.rank_all_projects')
    @patch('resume.resume_manager.ProjectSummarizer')
    def test_generate_user_resume_success(self, mock_summarizer_class, mock_rank):
        """Test successful generation of user resume from top projects."""
        mock_summarizer = Mock()
        mock_summarizer_class.return_value = mock_summarizer
        
        mock_rank.return_value = [
            {'project_id': 1, 'filename': 'project1.zip', 'score': 100},
            {'project_id': 2, 'filename': 'project2.zip', 'score': 85}
        ]
        
        mock_summarizer.generate_project_summary.return_value = {
            'languages': {'primary_language': 'Python', 'languages': ['Python', 'JavaScript']},
            'code_analysis': {}
        }
        
        result = ResumeManager.generate_user_resume("test_user", top_projects_count=2)
        
        assert result is not None
        assert result['total_projects_analyzed'] == 2
        assert result['top_projects_displayed'] == 2
        assert 'Python' in result['all_skills']
    
    @patch('resume.resume_manager.rank_all_projects')
    def test_generate_user_resume_no_projects(self, mock_rank):
        """Test resume generation when no projects exist."""
        mock_rank.return_value = []
        
        result = ResumeManager.generate_user_resume("test_user")
        
        assert result is None