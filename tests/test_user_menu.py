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
    
    @patch('builtins.input', side_effect=['4'])  # Back to main menu (option 4 now)
    @patch('sys.stdout', new_callable=StringIO)
    def test_user_account_menu_not_logged_in(self, mock_stdout, mock_input):
        """Test user account menu when not logged in"""
        user_account_menu()
        
        output = mock_stdout.getvalue()
        assert "You are not currently logged in" in output
        assert "1. Login to existing account" in output
        assert "2. Create new account" in output
        assert "3. Password display settings" in output
        assert "4. Back to main menu" in output
    
    @patch('builtins.input', side_effect=['3'])  # Back to main menu (option 3 for logged in)
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
        assert "2. Password display settings" in output
        assert "3. Back to main menu" in output


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
    @patch('cli.user_menus.get_password_input', return_value='')  # Empty password
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_empty_password(self, mock_stdout, mock_password_input, mock_input):
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
    @patch('cli.user_menus.get_password_input', return_value='')  # Empty password
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_registration_empty_password(self, mock_stdout, mock_password_input, mock_input):
        """Test registration with empty password"""
        handle_user_registration()
        
        output = mock_stdout.getvalue()
        assert "Password cannot be empty" in output
    
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('cli.user_menus.get_password_input', side_effect=['password123', 'different'])  # Different passwords
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_registration_password_mismatch(self, mock_stdout, mock_password_input, mock_input):
        """Test registration with mismatched passwords"""
        handle_user_registration()
        
        output = mock_stdout.getvalue()
        assert "Passwords do not match" in output
    
    @patch('account.user_manager.AuthManager.login')
    @patch('builtins.input', side_effect=['testuser', ''])  # Username and empty "Press Enter"
    @patch('cli.user_menus.get_password_input', return_value='password123')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_success(self, mock_stdout, mock_password_input, mock_input, mock_login):
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
    @patch('cli.user_menus.get_password_input', return_value='wrongpassword')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_user_login_failure(self, mock_stdout, mock_password_input, mock_input, mock_login):
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


class TestPasswordDisplaySettings:
    """Test password display settings functionality"""
    
    def setup_method(self):
        """Reset the AuthManager state before each test"""
        AuthManager.clear_session()
        # Reset password display setting to default
        import cli.user_menus
        cli.user_menus.SHOW_PASSWORD_AS_ASTERISK = True
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('builtins.input', side_effect=['1', ''])  # Choose asterisks and press enter
    @patch('sys.stdout', new_callable=StringIO)
    def test_set_password_display_mode_asterisks(self, mock_stdout, mock_input):
        """Test setting password display to asterisks"""
        from cli.user_menus import set_password_display_mode, SHOW_PASSWORD_AS_ASTERISK
        
        set_password_display_mode()
        
        output = mock_stdout.getvalue()
        assert "Password display set to asterisks (*)" in output
        
        # Import again to check the updated value
        import cli.user_menus
        assert cli.user_menus.SHOW_PASSWORD_AS_ASTERISK is True
    
    @patch('builtins.input', side_effect=['2', ''])  # Choose visible characters and press enter
    @patch('sys.stdout', new_callable=StringIO)
    def test_set_password_display_mode_visible(self, mock_stdout, mock_input):
        """Test setting password display to visible characters"""
        from cli.user_menus import set_password_display_mode
        
        set_password_display_mode()
        
        output = mock_stdout.getvalue()
        assert "Password display set to visible characters" in output
        
        # Import again to check the updated value
        import cli.user_menus
        assert cli.user_menus.SHOW_PASSWORD_AS_ASTERISK is False
    
    @patch('builtins.input', side_effect=['3', ''])  # Keep current setting and press enter
    @patch('sys.stdout', new_callable=StringIO)
    def test_set_password_display_mode_keep_current(self, mock_stdout, mock_input):
        """Test keeping current password display setting"""
        from cli.user_menus import set_password_display_mode
        
        set_password_display_mode()
        
        output = mock_stdout.getvalue()
        assert "Keeping current setting" in output
    
    @patch('builtins.input', side_effect=['invalid', '3', ''])  # Invalid then keep current
    @patch('sys.stdout', new_callable=StringIO)
    def test_set_password_display_mode_invalid_choice(self, mock_stdout, mock_input):
        """Test invalid choice in password display settings"""
        from cli.user_menus import set_password_display_mode
        
        set_password_display_mode()
        
        output = mock_stdout.getvalue()
        assert "Invalid choice. Keeping current setting." in output


class TestPasswordInput:
    """Test the custom password input functionality"""
    
    def test_get_password_input_asterisks(self):
        """Test password input with asterisks (cross-platform)"""
        from cli.user_menus import get_password_input
        
        # Try Windows path first
        try:
            import msvcrt
            # Windows - test with mocked msvcrt.getch
            with patch('msvcrt.getch', side_effect=[b'a', b'b', b'c', b'\r']):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=True)
                    
                assert password == "abc"
                output = mock_stdout.getvalue()
                assert "Test: ***" in output  # Should show three asterisks
                
        except ImportError:
            # Linux/Mac - test fallback behavior
            with patch('builtins.input', return_value='abc'):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=True)
                    
                assert password == "abc"
                output = mock_stdout.getvalue()
                assert "Password will be visible" in output  # Should show fallback message
    
    def test_get_password_input_visible(self):
        """Test password input with visible characters (cross-platform)"""
        from cli.user_menus import get_password_input
        
        # Try Windows path first
        try:
            import msvcrt
            # Windows - test with mocked msvcrt.getch
            with patch('msvcrt.getch', side_effect=[b'a', b'b', b'c', b'\r']):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=False)
                    
                assert password == "abc"
                output = mock_stdout.getvalue()
                assert "Test: abc" in output  # Should show actual characters
                
        except ImportError:
            # Linux/Mac - test fallback behavior
            with patch('builtins.input', return_value='abc'):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=False)
                    
                assert password == "abc"
                output = mock_stdout.getvalue()
                assert "Password will be visible" in output  # Should show fallback message
    
    def test_get_password_input_backspace(self):
        """Test backspace functionality in password input (cross-platform)"""
        from cli.user_menus import get_password_input
        
        # Try Windows path first
        try:
            import msvcrt
            # Windows - test with mocked msvcrt.getch with backspace sequence
            with patch('msvcrt.getch', side_effect=[b'a', b'b', b'\x08', b'c', b'\r']):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=True)
                    
                assert password == "ac"  # 'ab' with 'b' removed by backspace, then 'c'
                
        except ImportError:
            # Linux/Mac - test fallback behavior (backspace not applicable in fallback)
            with patch('builtins.input', return_value='ac'):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    password = get_password_input("Test: ", show_asterisk=True)
                    
                assert password == "ac"
                output = mock_stdout.getvalue()
                assert "Password will be visible" in output
    
    def test_get_password_input_keyboard_interrupt(self):
        """Test Ctrl+C handling in password input (cross-platform)"""
        from cli.user_menus import get_password_input
        
        # Try Windows path first
        try:
            import msvcrt
            # Windows - test with mocked msvcrt.getch with Ctrl+C
            with patch('msvcrt.getch', side_effect=[b'a', b'b', b'\x03']):
                with pytest.raises(KeyboardInterrupt):
                    get_password_input("Test: ", show_asterisk=True)
                    
        except ImportError:
            # Linux/Mac - test fallback KeyboardInterrupt behavior
            with patch('builtins.input', side_effect=KeyboardInterrupt):
                with pytest.raises(KeyboardInterrupt):
                    get_password_input("Test: ", show_asterisk=True)


if __name__ == '__main__':
    pytest.main([__file__])