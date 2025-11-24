# tests/test_user_manager.py

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import the module to test
from account.user_manager import AuthManager


class TestAuthManager:
    """Test class for AuthManager functionality"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    # Test session management methods
    def test_initial_state(self):
        """Test that AuthManager starts with no user logged in"""
        assert AuthManager.get_current_user() is None
        assert AuthManager.is_user_logged_in() is False
        assert AuthManager.get_current_username() is None
    
    def test_clear_session(self):
        """Test clearing session"""
        # Manually set a user to test clearing
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        assert AuthManager.is_user_logged_in() is True
        
        AuthManager.clear_session()
        assert AuthManager.get_current_user() is None
        assert AuthManager.is_user_logged_in() is False
        assert AuthManager.get_current_username() is None
    
    # Test registration functionality
    @patch('account.user_manager.is_username_available')
    @patch('account.user_manager.create_user')
    def test_register_success(self, mock_create_user, mock_is_username_available):
        """Test successful user registration"""
        mock_is_username_available.return_value = True
        mock_create_user.return_value = 123
        
        result = AuthManager.register("newuser", "password123")
        
        assert result['success'] is True
        assert result['message'] == 'Registration successful'
        assert result['user_id'] == 123
        mock_is_username_available.assert_called_once_with("newuser")
        mock_create_user.assert_called_once_with("newuser", "password123")
    
    def test_register_empty_username(self):
        """Test registration with empty username"""
        result = AuthManager.register("", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Username cannot be empty'
        assert result['user_id'] is None
    
    def test_register_whitespace_username(self):
        """Test registration with whitespace-only username"""
        result = AuthManager.register("   ", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Username cannot be empty'
        assert result['user_id'] is None
    
    def test_register_short_password(self):
        """Test registration with password too short"""
        result = AuthManager.register("newuser", "123")
        
        assert result['success'] is False
        assert result['message'] == 'Password must be at least 6 characters long'
        assert result['user_id'] is None
    
    def test_register_empty_password(self):
        """Test registration with empty password"""
        result = AuthManager.register("newuser", "")
        
        assert result['success'] is False
        assert result['message'] == 'Password must be at least 6 characters long'
        assert result['user_id'] is None
    
    @patch('account.user_manager.is_username_available')
    def test_register_username_exists(self, mock_is_username_available):
        """Test registration when username already exists"""
        mock_is_username_available.return_value = False
        
        result = AuthManager.register("existinguser", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Username already exists'
        assert result['user_id'] is None
    
    @patch('account.user_manager.is_username_available')
    @patch('account.user_manager.create_user')
    def test_register_creation_failure(self, mock_create_user, mock_is_username_available):
        """Test registration when user creation fails"""
        mock_is_username_available.return_value = True
        mock_create_user.return_value = None
        
        result = AuthManager.register("newuser", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Registration failed, please try again later'
        assert result['user_id'] is None
    
    # Test login functionality
    @patch('account.user_manager.login_user')
    @patch('account.user_manager.get_user_by_username')
    def test_login_success(self, mock_get_user, mock_login_user):
        """Test successful login"""
        mock_login_user.return_value = True
        mock_user_info = {
            'user_id': 1,
            'user_name': 'testuser',
            'create_time': '2024-01-01',
            'last_login_time': '2024-01-02',
            'is_login': True
        }
        mock_get_user.return_value = mock_user_info
        
        result = AuthManager.login("testuser", "password123")
        
        assert result['success'] is True
        assert result['message'] == 'Login successful'
        assert result['user_info'] == mock_user_info
        assert AuthManager.get_current_user() == mock_user_info
        assert AuthManager.is_user_logged_in() is True
        assert AuthManager.get_current_username() == "testuser"
    
    def test_login_empty_username(self):
        """Test login with empty username"""
        result = AuthManager.login("", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Username cannot be empty'
        assert result['user_info'] is None
    
    def test_login_empty_password(self):
        """Test login with empty password"""
        result = AuthManager.login("testuser", "")
        
        assert result['success'] is False
        assert result['message'] == 'Password cannot be empty'
        assert result['user_info'] is None
    
    @patch('account.user_manager.login_user')
    def test_login_invalid_credentials(self, mock_login_user):
        """Test login with invalid credentials"""
        mock_login_user.return_value = False
        
        result = AuthManager.login("testuser", "wrongpassword")
        
        assert result['success'] is False
        assert result['message'] == 'Invalid username or password'
        assert result['user_info'] is None
        assert AuthManager.is_user_logged_in() is False
    
    @patch('account.user_manager.login_user')
    @patch('account.user_manager.get_user_by_username')
    def test_login_user_info_retrieval_failure(self, mock_get_user, mock_login_user):
        """Test login when user info retrieval fails"""
        mock_login_user.return_value = True
        mock_get_user.return_value = None
        
        result = AuthManager.login("testuser", "password123")
        
        assert result['success'] is False
        assert result['message'] == 'Login failed: Unable to retrieve user information'
        assert result['user_info'] is None
        assert AuthManager.is_user_logged_in() is False
    
    def test_login_when_already_logged_in(self):
        """Test login attempt when someone is already logged in"""
        # Manually set a logged-in user
        AuthManager._current_user = {'user_name': 'currentuser', 'user_id': 1}
        
        result = AuthManager.login("newuser", "password123")
        
        assert result['success'] is False
        assert 'currentuser' in result['message']
        assert 'already logged in' in result['message']
        assert result['user_info'] is None
    
    # Test logout functionality
    @patch('account.user_manager.logout_user')
    def test_logout_success_with_username(self, mock_logout_user):
        """Test successful logout with username provided"""
        mock_logout_user.return_value = True
        # Set current user
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        result = AuthManager.logout("testuser")
        
        assert result['success'] is True
        assert result['message'] == 'Logout successful'
        assert AuthManager.is_user_logged_in() is False
        mock_logout_user.assert_called_once_with("testuser")
    
    @patch('account.user_manager.logout_user')
    def test_logout_success_without_username(self, mock_logout_user):
        """Test successful logout without username (current user)"""
        mock_logout_user.return_value = True
        # Set current user
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        result = AuthManager.logout()
        
        assert result['success'] is True
        assert result['message'] == 'Logout successful'
        assert AuthManager.is_user_logged_in() is False
        mock_logout_user.assert_called_once_with("testuser")
    
    def test_logout_no_user_logged_in(self):
        """Test logout when no user is logged in"""
        result = AuthManager.logout()
        
        assert result['success'] is False
        assert result['message'] == 'No user is currently logged in'
    
    def test_logout_empty_username(self):
        """Test logout with empty username"""
        result = AuthManager.logout("")
        
        assert result['success'] is False
        assert result['message'] == 'Username cannot be empty'
    
    def test_logout_wrong_user(self):
        """Test logout attempt for different user than currently logged in"""
        # Set current user
        AuthManager._current_user = {'user_name': 'currentuser', 'user_id': 1}
        
        result = AuthManager.logout("differentuser")
        
        assert result['success'] is False
        assert 'Cannot logout "differentuser"' in result['message']
        assert 'Currently logged in as "currentuser"' in result['message']
    
    @patch('account.user_manager.logout_user')
    def test_logout_database_failure(self, mock_logout_user):
        """Test logout when database operation fails"""
        mock_logout_user.return_value = False
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        result = AuthManager.logout("testuser")
        
        assert result['success'] is False
        assert result['message'] == 'Logout failed, user may not exist or is not logged in'
        # Session should not be cleared if database operation fails
        assert AuthManager.is_user_logged_in() is True


class TestAuthManagerIntegration:
    """Integration tests for complete login/logout flow"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('account.user_manager.login_user')
    @patch('account.user_manager.get_user_by_username')
    @patch('account.user_manager.logout_user')
    def test_complete_login_logout_flow(self, mock_logout_user, mock_get_user, mock_login_user):
        """Test complete flow: login -> check status -> logout"""
        # Setup mocks for login
        mock_login_user.return_value = True
        mock_user_info = {'user_name': 'testuser', 'user_id': 1}
        mock_get_user.return_value = mock_user_info
        mock_logout_user.return_value = True
        
        # Initial state
        assert not AuthManager.is_user_logged_in()
        
        # Login
        login_result = AuthManager.login("testuser", "password123")
        assert login_result['success'] is True
        assert AuthManager.is_user_logged_in() is True
        assert AuthManager.get_current_username() == "testuser"
        
        # Logout
        logout_result = AuthManager.logout()
        assert logout_result['success'] is True
        assert not AuthManager.is_user_logged_in()
        assert AuthManager.get_current_user() is None
    
    @patch('account.user_manager.is_username_available')
    @patch('account.user_manager.create_user')
    @patch('account.user_manager.login_user')
    @patch('account.user_manager.get_user_by_username')
    def test_register_then_login_flow(self, mock_get_user, mock_login_user, mock_create_user, mock_is_username_available):
        """Test complete flow: register -> login"""
        # Setup mocks for registration
        mock_is_username_available.return_value = True
        mock_create_user.return_value = 123
        
        # Setup mocks for login
        mock_login_user.return_value = True
        mock_user_info = {'user_name': 'newuser', 'user_id': 123}
        mock_get_user.return_value = mock_user_info
        
        # Register
        register_result = AuthManager.register("newuser", "password123")
        assert register_result['success'] is True
        assert register_result['user_id'] == 123
        
        # Login with new account
        login_result = AuthManager.login("newuser", "password123")
        assert login_result['success'] is True
        assert AuthManager.get_current_username() == "newuser"


if __name__ == '__main__':
    pytest.main([__file__])