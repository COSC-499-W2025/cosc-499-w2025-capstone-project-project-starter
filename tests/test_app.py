"""
Tests for application initialization and setup
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app import initialize_app, ensure_user_preferences_schema


class TestEnsureUserPreferencesSchema:
    """Test user preferences schema migration"""
    
    @patch('app.get_connection')
    def test_ensure_user_preferences_schema_table_exists(self, mock_get_connection):
        """Test schema update when table exists"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_get_connection.return_value = mock_conn
        
        # Table exists
        mock_cursor.fetchone.return_value = (True,)
        
        ensure_user_preferences_schema()
        
        # Should check if table exists, then add column
        assert mock_cursor.execute.call_count >= 2
        mock_conn.commit.assert_called_once()
    
    @patch('app.get_connection')
    def test_ensure_user_preferences_schema_table_not_exists(self, mock_get_connection):
        """Test schema update when table doesn't exist"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_get_connection.return_value = mock_conn
        
        # Table doesn't exist
        mock_cursor.fetchone.return_value = (False,)
        
        with pytest.raises(Exception, match="user_preferences table does not exist"):
            ensure_user_preferences_schema()
    
    @patch('app.get_connection')
    def test_ensure_user_preferences_schema_error(self, mock_get_connection):
        """Test error handling in schema update"""
        mock_get_connection.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception):
            ensure_user_preferences_schema()


class TestInitializeApp:
    """Test application initialization"""
    
    @patch('app.ensure_user_preferences_schema')
    @patch('app.get_connection')
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_success(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_consent_manager_class,
        mock_collab_manager_class,
        mock_get_connection,
        mock_ensure_schema
    ):
        """Test successful application initialization"""
        # Setup mocks
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = True
        mock_collab_manager_class.return_value = mock_collab_manager
        
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        result = initialize_app()
        
        # Verify all initialization steps were called
        mock_init_uploaded.assert_called_once()
        mock_init_user_info.assert_called_once()
        mock_init_ranking.assert_called_once()
        mock_resume_manager.init_resume_table.assert_called_once()
        mock_consent_manager.initialize.assert_called_once()
        mock_consent_manager.request_consent_if_needed.assert_called_once()
        mock_collab_manager.request_collaborative_if_needed.assert_called_once()
        mock_ensure_schema.assert_called_once()
        mock_get_connection.assert_called_once()
        mock_conn.close.assert_called_once()
        
        # Should return tuple of managers
        assert result is not None
        assert len(result) == 2
        assert result[0] == mock_consent_manager
        assert result[1] == mock_collab_manager
    
    @patch('app.get_connection')
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_consent_not_granted(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_consent_manager_class,
        mock_collab_manager_class,
        mock_get_connection
    ):
        """Test initialization when consent is not granted"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = False
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager_class.return_value = mock_collab_manager
        
        result = initialize_app()
        
        # Should return None when consent not granted
        assert result is None
        mock_consent_manager.request_consent_if_needed.assert_called_once()
    
    @patch('app.get_connection')
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_collaborative_not_granted(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_consent_manager_class,
        mock_collab_manager_class,
        mock_get_connection
    ):
        """Test initialization when collaborative consent is not granted"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = False
        mock_collab_manager_class.return_value = mock_collab_manager
        
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        result = initialize_app()
        
        # Should still succeed but collaborative not granted
        assert result is not None
        mock_collab_manager.request_collaborative_if_needed.assert_called_once()
    
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_database_init_error(self, mock_init_uploaded):
        """Test initialization when database table initialization fails"""
        mock_init_uploaded.side_effect = Exception("Database initialization error")
        
        result = initialize_app()
        
        # Should return None on initialization error
        assert result is None
    
    @patch('app.ensure_user_preferences_schema')
    @patch('app.get_connection')
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_database_connection_fails(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_consent_manager_class,
        mock_collab_manager_class,
        mock_get_connection,
        mock_ensure_schema
    ):
        """Test initialization when database connection fails"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = True
        mock_collab_manager_class.return_value = mock_collab_manager
        
        # Database connection returns None
        mock_get_connection.return_value = None
        
        result = initialize_app()
        
        # Should return None when database connection fails
        assert result is None
    
    @patch('app.ensure_user_preferences_schema')
    @patch('app.get_connection')
    @patch('app.CollaborativeManager')
    @patch('app.ConsentManager')
    @patch('app.ResumeManager')
    @patch('app.init_ranking_storage_table')
    @patch('app.init_user_informations_table')
    @patch('app.init_uploaded_files_table')
    def test_initialize_app_database_connection_exception(
        self,
        mock_init_uploaded,
        mock_init_user_info,
        mock_init_ranking,
        mock_resume_manager,
        mock_consent_manager_class,
        mock_collab_manager_class,
        mock_get_connection,
        mock_ensure_schema
    ):
        """Test initialization when database connection raises exception"""
        mock_consent_manager = MagicMock()
        mock_consent_manager.request_consent_if_needed.return_value = True
        mock_consent_manager_class.return_value = mock_consent_manager
        
        mock_collab_manager = MagicMock()
        mock_collab_manager.request_collaborative_if_needed.return_value = True
        mock_collab_manager_class.return_value = mock_collab_manager
        
        # Database connection raises exception (in ensure_user_preferences_schema)
        # The exception is raised and not caught, so it propagates
        mock_ensure_schema.side_effect = Exception("Connection error")
        
        # Exception should propagate since ensure_user_preferences_schema raises it
        with pytest.raises(Exception, match="Connection error"):
            initialize_app()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

