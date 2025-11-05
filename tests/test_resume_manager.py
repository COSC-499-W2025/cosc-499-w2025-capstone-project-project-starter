import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.resume_manager import ResumeManager


class TestResumeManagerTableInitialization:
    """Test database table creation."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_init_resume_tables_success(self, mock_with_db_cursor):
        """Test successful initialization of resume tables."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Execute
        result = ResumeManager.init_resume_tables()
        
        # Verify
        assert result == True
        assert mock_cursor.execute.call_count == 3  # 2 tables + 1 index
        assert mock_with_db_cursor.called
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_init_resume_tables_failure(self, mock_with_db_cursor):
        """Test handling of table initialization failure."""
        # Mock database connection failure
        mock_with_db_cursor.side_effect = Exception("Database error")
        
        # Execute
        result = ResumeManager.init_resume_tables()
        
        # Verify
        assert result == False


class TestProjectResumeStorage:
    """Test project-specific resume storage and retrieval."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_store_project_resume_success(self, mock_with_db_cursor):
        """Test successful storage of project resume."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Test data
        project_id = 1
        user_id = "test_user"
        resume_data = {
            'project_name': 'Test Project',
            'skills': ['Python', 'JavaScript'],
            'metrics': {'files': 10, 'lines': 500}
        }
        
        # Execute
        result = ResumeManager.store_project_resume(project_id, user_id, resume_data)
        
        # Verify
        assert result == True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO project_resumes" in call_args[0][0]
        assert call_args[0][1][0] == project_id
        assert call_args[0][1][1] == user_id
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_project_resume_success(self, mock_with_db_cursor):
        """Test successful retrieval of project resume."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock resume data from database
        resume_data = '{"project_name": "Test Project", "skills": ["Python"]}'
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        updated_at = datetime(2024, 1, 1, 11, 0, 0)
        mock_cursor.fetchone.return_value = (resume_data, created_at, updated_at)
        
        # Execute
        result = ResumeManager.get_project_resume(1, "test_user")
        
        # Verify
        assert result is not None
        assert result['resume_item_data'] == resume_data
        assert result['created_at'] == created_at
        assert result['updated_at'] == updated_at
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_project_resume_not_found(self, mock_with_db_cursor):
        """Test retrieval when project resume doesn't exist."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock empty result
        mock_cursor.fetchone.return_value = None
        
        # Execute
        result = ResumeManager.get_project_resume(999, "test_user")
        
        # Verify
        assert result is None


class TestUserResumeStorage:
    """Test user-aggregated resume storage and retrieval."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_store_user_resume_success(self, mock_with_db_cursor):
        """Test successful storage of user resume."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Test data
        user_id = "test_user"
        resume_data = {
            'total_projects': 5,
            'all_skills': ['Python', 'JavaScript', 'React'],
            'total_experience_duration': '12 months'
        }
        
        # Execute
        result = ResumeManager.store_user_resume(user_id, resume_data)
        
        # Verify
        assert result == True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO generated_resumes" in call_args[0][0]
        assert call_args[0][1][0] == user_id
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_user_resume_success(self, mock_with_db_cursor):
        """Test successful retrieval of user resume."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock resume data from database
        resume_data = '{"total_projects": 5, "all_skills": ["Python", "JavaScript"]}'
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        updated_at = datetime(2024, 1, 1, 11, 0, 0)
        mock_cursor.fetchone.return_value = (resume_data, created_at, updated_at)
        
        # Execute
        result = ResumeManager.get_user_resume("test_user")
        
        # Verify
        assert result is not None
        assert result['resume_data'] == resume_data
        assert result['created_at'] == created_at
        assert result['updated_at'] == updated_at


class TestResumeOperations:
    """Test resume operations (delete, get all)."""
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_get_all_project_resumes_success(self, mock_with_db_cursor):
        """Test retrieval of all project resumes for a user."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock multiple resume records
        mock_cursor.fetchall.return_value = [
            (1, 1, '{"project_name": "Project 1"}', datetime(2024, 1, 1), datetime(2024, 1, 1)),
            (2, 2, '{"project_name": "Project 2"}', datetime(2024, 1, 2), datetime(2024, 1, 2)),
        ]
        
        # Execute
        result = ResumeManager.get_all_project_resumes("test_user")
        
        # Verify
        assert len(result) == 2
        assert result[0]['project_id'] == 1
        assert result[1]['project_id'] == 2
    
    @patch('resume.resume_manager.with_db_cursor')
    def test_delete_project_resume_success(self, mock_with_db_cursor):
        """Test successful deletion of project resume."""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Execute
        result = ResumeManager.delete_project_resume(1, "test_user")
        
        # Verify
        assert result == True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "DELETE FROM project_resumes" in call_args[0][0]