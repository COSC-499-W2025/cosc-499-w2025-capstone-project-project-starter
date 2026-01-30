"""
Tests for application initialization and setup
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app import initialize_database, initialize_managers, ensure_user_preferences_schema


class TestEnsureUserPreferencesSchema:
    """Test user preferences schema migration"""
    
    @patch('config.db_config.with_db_cursor')
    def test_ensure_user_preferences_schema_table_exists(self, mock_with_db_cursor):
        """Test schema update when table exists"""
        mock_cursor = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        mock_with_db_cursor.return_value = mock_context
        
        ensure_user_preferences_schema()
        
        # Should add column if not exists
        assert mock_cursor.execute.called
        mock_with_db_cursor.assert_called_once()
    
    @patch('config.db_config.with_db_cursor')
    def test_ensure_user_preferences_schema_table_not_exists(self, mock_with_db_cursor):
        """Test schema update when table doesn't exist"""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("user_preferences table does not exist")
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        mock_with_db_cursor.return_value = mock_context
        
        # Exception should be caught and printed, not raised
        ensure_user_preferences_schema()
    
    @patch('config.db_config.with_db_cursor')
    def test_ensure_user_preferences_schema_error(self, mock_with_db_cursor):
        """Test error handling in schema update"""
        mock_with_db_cursor.side_effect = Exception("Database connection error")
        
        # Exception should be caught and printed, not raised
        ensure_user_preferences_schema()


class TestInitializeDatabase:
    """Test database initialization"""
    
    @patch('app.ensure_user_preferences_schema')
    @patch('config.db_config.with_db_cursor')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_database_success(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_with_db_cursor,
        mock_ensure_schema
    ):
        """Test successful database initialization"""
        # Setup mocks
        mock_cursor = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        mock_with_db_cursor.return_value = mock_context
        
        result = initialize_database()
        
        # Verify all initialization steps were called
        mock_init_uploaded.assert_called_once()
        mock_init_user_info.assert_called_once()
        mock_init_ranking.assert_called_once()
        mock_resume_manager.init_resume_table.assert_called_once()
        mock_ensure_schema.assert_called_once()
        assert mock_with_db_cursor.called
        
        # Should return True on success
        assert result is True
    
    @patch('app.init_uploaded_files_table')
    def test_initialize_database_table_init_error(self, mock_init_uploaded):
        """Test database initialization when table initialization fails"""
        mock_init_uploaded.side_effect = Exception("Database initialization error")
        
        result = initialize_database()
        
        # Should return False on initialization error
        assert result is False
    
    @patch('app.ensure_user_preferences_schema')
    @patch('config.db_config.with_db_cursor')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_database_connection_fails(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_with_db_cursor,
        mock_ensure_schema
    ):
        """Test database initialization when connection fails"""
        # Database connection fails
        mock_with_db_cursor.side_effect = ConnectionError("Could not connect to database")
        
        result = initialize_database()
        
        # Should return False when database connection fails
        assert result is False


class TestInitializeManagers:
    """Test manager initialization"""
    
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    def test_initialize_managers_success(
        self,
        mock_consent_manager_class,
        mock_collab_manager_class
    ):
        """Test successful manager initialization"""
        # Setup mocks
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = True
        mock_collab_manager_class.return_value = mock_collab_manager
        
        result = initialize_managers()
        
        # Verify initialization steps were called
        mock_consent_manager.initialize.assert_called_once()
        mock_consent_manager.request_consent_if_needed.assert_called_once()
        mock_collab_manager.request_collaborative_if_needed.assert_called_once()
        
        # Should return tuple of managers
        assert result is not None
        assert len(result) == 2
        assert result[0] == mock_consent_manager
        assert result[1] == mock_collab_manager
    
    @patch('app.ConsentManager')
    def test_initialize_managers_consent_manager_error(self, mock_consent_manager_class):
        """Test manager initialization when ConsentManager fails"""
        # ConsentManager raises ValueError (e.g., no user logged in)
        mock_consent_manager_class.side_effect = ValueError("No user is currently logged in")
        
        result = initialize_managers()
        
        # Should return None when ConsentManager initialization fails
        assert result is None
    
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    def test_initialize_managers_consent_not_granted(
        self,
        mock_consent_manager_class,
        mock_collab_manager_class
    ):
        """Test manager initialization when consent is not granted"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = False
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager_class.return_value = mock_collab_manager
        
        result = initialize_managers()
        
        # Should return None when consent not granted
        assert result is None
        mock_consent_manager.request_consent_if_needed.assert_called_once()
    
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    def test_initialize_managers_collaborative_not_granted(
        self,
        mock_consent_manager_class,
        mock_collab_manager_class
    ):
        """Test manager initialization when collaborative consent is not granted"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = False
        mock_collab_manager_class.return_value = mock_collab_manager
        
        result = initialize_managers()
        
        # Should still succeed but collaborative not granted
        assert result is not None
        mock_collab_manager.request_collaborative_if_needed.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

