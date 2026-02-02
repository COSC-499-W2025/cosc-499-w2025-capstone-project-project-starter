# tests/test_project_manager.py
import sys
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from src.project_manager import list_projects, list_projects_chronologically, list_project_files, get_project_by_id, get_project_count


class TestProjectManager:
    """Test suite for project_manager functionality"""
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the list_projects function when there are projects with files
    def test_list_projects_with_files(self, mock_with_db_cursor):
        """Test that projects are listed with file counts"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database results with nested folder structure
        mock_projects = [
            (1, "project_a.zip", "uploaded", '{"files": ["folder/file1.py", "folder/file2.js", "folder/"]}', datetime(2024, 1, 1, 10, 0, 0), b"thumb"),
            (2, "project_b.zip", "uploaded", '{"files": ["readme.md", "src/main.py", "tests/test.py"]}', datetime(2024, 1, 2, 11, 0, 0), None)
        ]
        mock_cursor.fetchall.return_value = mock_projects
        
        # Call the function with user_name parameter for data isolation
        result = list_projects('test_user')
        
        # Verify database operations
        mock_with_db_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        # Verify return value structure (should return list of project dicts)
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['filename'] == "project_a.zip"
        assert result[0]['file_count'] == 2  # 2 files (excluding directory "folder/")
        assert result[0]['created_at'] == datetime(2024, 1, 1, 10, 0, 0)
        assert result[0]['has_thumbnail'] is True
        
        assert result[1]['id'] == 2
        assert result[1]['filename'] == "project_b.zip"
        assert result[1]['file_count'] == 3  # 3 files
        assert result[1]['created_at'] == datetime(2024, 1, 2, 11, 0, 0)
        assert result[1]['has_thumbnail'] is False
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the list_projects function when there are no projects in the database
    def test_list_projects_no_projects(self, mock_with_db_cursor):
        """Test listing when no projects exist"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock empty results
        mock_cursor.fetchall.return_value = []
        
        # Call the function with user_name parameter
        result = list_projects('test_user')
        
        # Verify return value
        assert result == []
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the list_projects function when the database connection fails
    def test_list_projects_database_connection_failure(self, mock_with_db_cursor):
        """Test handling of database connection failure"""
        # Mock database connection failure
        mock_with_db_cursor.side_effect = ConnectionError("Could not connect to database")
        
        # Call the function with user_name parameter
        result = list_projects('test_user')
        
        # Verify return value
        assert result == []
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the get_project_by_id function
    def test_get_project_by_id_success(self, mock_with_db_cursor):
        """Test successful project retrieval by ID"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # FIX: Updated mock to match the 4-column SELECT query (id, filename, metadata, created_at)
        # Old mock had 6 columns which caused the crash
        mock_project = (
            1, 
            "test_project.zip", 
            '{"files": ["file1.py"]}', 
            datetime(2024, 1, 1, 10, 0, 0)
        )
        mock_cursor.fetchone.return_value = mock_project
        
        # Call the function with user_name parameter for data isolation
        result = get_project_by_id(1, 'test_user')
        
        # Verify database operations
        mock_cursor.execute.assert_called_once()
        
        # FIX: Updated assertions to match the new nested structure returned by get_project_by_id
        # The new function returns a dict with 'project_info' containing the metadata
        assert result['project_info']['id'] == 1
        assert result['project_info']['filename'] == "test_project.zip"
        # Verify the created_at was converted to string as expected by the new logic
        assert result['project_info']['created_at'] == datetime(2024, 1, 1, 10, 0, 0).isoformat()
        assert result['files'] == ["file1.py"]
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the get_project_by_id function when the project does not exist
    def test_get_project_by_id_not_found(self, mock_with_db_cursor):
        """Test project retrieval when project doesn't exist"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock empty result
        mock_cursor.fetchone.return_value = None
        
        # Call the function with user_name parameter
        result = get_project_by_id(999, 'test_user')
        
        # Verify return value
        assert result is None
    
    @patch('src.project_manager.with_db_cursor')
    # this test will test the list_project_files function
    def test_list_project_files_success(self, mock_with_db_cursor):
        """Test listing files within a project"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database result with metadata containing files
        mock_metadata = '{"files": ["folder/file1.py", "folder/file2.js", "folder/", "readme.md"]}'
        
        # FIX: The query selects 'filename, metadata' (2 columns). Mock must provide both.
        mock_cursor.fetchone.return_value = ("test.zip", mock_metadata)
        
        # Call the function with user_name parameter for data isolation
        result = list_project_files(1, 'test_user')
        
        # Verify database operations
        mock_with_db_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        # Verify return value (should return only actual files, not directories)
        assert len(result) == 3
        assert "folder/file1.py" in result
        assert "folder/file2.js" in result
        assert "readme.md" in result
        assert "folder/" not in result  # Directory should be excluded
    
    @patch('src.project_manager.with_db_cursor')
    def test_list_project_files_not_found(self, mock_with_db_cursor):
        """Test listing files when project doesn't exist"""
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock empty result
        mock_cursor.fetchone.return_value = None
        
        # Call the function with user_name parameter
        result = list_project_files(999, 'test_user')
        
        # Verify return value
        assert result == []
    
    @patch('src.project_manager.with_db_cursor')
    def test_get_project_count_success(self, mock_with_db_cursor):
        """Test successful project count retrieval"""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        mock_cursor.fetchone.return_value = (5,)
        
        # Call the function with user_name parameter for data isolation
        result = get_project_count('test_user')
        
        mock_cursor.execute.assert_called_once()
        assert result == 5
    
    @patch('src.project_manager.with_db_cursor')
    def test_list_projects_chronologically(self, mock_with_db_cursor):
        """Test chronological project listing"""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # FIX: The query selects 6 columns: id, filename, status, metadata, created_at, thumbnail.
        # Added 'None' (for thumbnail) to match column count and prevent unpacking error.
        mock_projects = [
            (2, "project_b.zip", "uploaded", '{"files": ["file2.py"]}', datetime(2024, 1, 2, 11, 0, 0), None),
            (1, "project_a.zip", "uploaded", '{"files": ["file1.py"]}', datetime(2024, 1, 1, 10, 0, 0), None)
        ]
        mock_cursor.fetchall.return_value = mock_projects
        
        # Call the function with user_name parameter for data isolation
        result = list_projects_chronologically('test_user')
        
        mock_cursor.execute.assert_called_once()
        assert len(result) == 2
        assert result[0]['id'] == 2
        assert result[1]['id'] == 1
        assert result[0]['created_at'] == datetime(2024, 1, 2, 11, 0, 0)
        assert result[1]['created_at'] == datetime(2024, 1, 1, 10, 0, 0)
    
    @patch('src.project_manager.with_db_cursor')
    def test_list_projects_chronologically_no_projects(self, mock_with_db_cursor):
        """Test chronological listing when no projects exist"""
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        mock_cursor.fetchall.return_value = []
        
        # Call the function with user_name parameter
        result = list_projects_chronologically('test_user')
        
        assert result == []
    
    @patch('src.project_manager.with_db_cursor')
    def test_list_projects_chronologically_connection_error(self, mock_with_db_cursor):
        """Test chronological listing with connection error"""
        mock_with_db_cursor.side_effect = ConnectionError("Connection failed")
        
        # Call the function with user_name parameter
        result = list_projects_chronologically('test_user')
        
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])