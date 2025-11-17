# tests/test_user_menu.py

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import the modules to test
from cli.user_menus import user_account_menu, handle_user_login, handle_user_logout, handle_user_registration
from account.user_manager import AuthManager


class TestUserAccountMenu:
    """Test class for user account menu functionality"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('builtins.input', side_effect=['3'])  # Back to main menu
    @patch('sys.stdout', new_callable=StringIO)
    def test_user_account_menu_not_logged_in(self, mock_stdout, mock_input):
        """Test user account menu when not logged in"""
        user_account_menu()
        
        output = mock_stdout.getvalue()
        assert "You are not currently logged in" in output
        assert "1. Login to existing account" in output
        assert "2. Create new account" in output
        assert "3. Back to main menu" in output
    
    @patch('builtins.input', side_effect=['2'])  # Back to main menu
    @patch('sys.stdout', new_callable=StringIO)
    def test_user_account_menu_logged_in(self, mock_stdout, mock_input):
        """Test user account menu when logged in"""
        # Set up a logged in user
        AuthManager._current_user = {
            'user_id': 1,
            'user_name': 'testuser',
            'create_time': '2024-01-01 10:00:00',
            'last_login_time': '2024-01-01 12:00:00'
        }
        
        user_account_menu()
        
        output = mock_stdout.getvalue()
        assert "Currently logged in as: testuser" in output
        assert "User ID: 1" in output
        assert "1. Logout" in output
        assert "2. Back to main menu" in output


class TestUserLoginRegistration:
    """Test user login and registration handlers"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('builtins.input', side_effect=['', ''])  # Empty username and empty "Press Enter"
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_empty_username(self, mock_stdout, mock_input):
        """Test login with empty username"""
        handle_user_login()
        
        output = mock_stdout.getvalue()
        assert "Username cannot be empty" in output
    
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('getpass.getpass', return_value='')  # Empty password
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_empty_password(self, mock_stdout, mock_getpass, mock_input):
        """Test login with empty password"""
        handle_user_login()
        
        output = mock_stdout.getvalue()
        assert "Password cannot be empty" in output
    
    @patch('builtins.input', side_effect=['', ''])  # Empty username and empty "Press Enter"
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_registration_empty_username(self, mock_stdout, mock_input):
        """Test registration with empty username"""
        handle_user_registration()
        
        output = mock_stdout.getvalue()
        assert "Username cannot be empty" in output
    
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('getpass.getpass', return_value='')  # Empty password
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_registration_empty_password(self, mock_stdout, mock_getpass, mock_input):
        """Test registration with empty password"""
        handle_user_registration()
        
        output = mock_stdout.getvalue()
        assert "Password cannot be empty" in output
    
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('getpass.getpass', side_effect=['password123', 'different'])  # Different passwords
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_registration_password_mismatch(self, mock_stdout, mock_getpass, mock_input):
        """Test registration with mismatched passwords"""
        handle_user_registration()
        
        output = mock_stdout.getvalue()
        assert "Passwords do not match" in output
    
    @patch('account.user_manager.AuthManager.login')
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('getpass.getpass', return_value='password123')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_success(self, mock_stdout, mock_getpass, mock_input, mock_login):
        """Test successful login"""
        mock_login.return_value = {
            'success': True,
            'message': 'Login successful',
            'user_info': {'user_name': 'testuser'}
        }
        
        handle_user_login()
        
        output = mock_stdout.getvalue()
        assert "✓ Login successful" in output
        assert "Welcome back, testuser!" in output
    
    @patch('account.user_manager.AuthManager.login')
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('getpass.getpass', return_value='wrongpassword')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_failure(self, mock_stdout, mock_getpass, mock_input, mock_login):
        """Test failed login"""
        mock_login.return_value = {
            'success': False,
            'message': 'Invalid username or password',
            'user_info': None
        }
        
        handle_user_login()
        
        output = mock_stdout.getvalue()
        assert "✗ Invalid username or password" in output


class TestLogoutHandler:
    """Test logout handler"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('builtins.input', side_effect=['y', ''])  # Confirm logout and "Press Enter"
    @patch('account.user_manager.AuthManager.logout')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_logout_success(self, mock_stdout, mock_logout, mock_input):
        """Test successful logout"""
        # Set up logged in user
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        mock_logout.return_value = {
            'success': True,
            'message': 'Logout successful'
        }
        
        handle_user_logout()
        
        output = mock_stdout.getvalue()
        assert "✓ Logout successful" in output
        assert "You have been logged out" in output
    
    @patch('builtins.input', return_value='n')  # Don't confirm logout
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_logout_cancelled(self, mock_stdout, mock_input):
        """Test cancelled logout"""
        # Set up logged in user
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        handle_user_logout()
        
        # Function should return without doing anything when cancelled
        # Just make sure no error occurs


if __name__ == '__main__':
    pytest.main([__file__])