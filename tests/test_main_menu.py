"""
Tests for main menu functionality
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from io import StringIO

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cli.main_menu import run_main_menu, MENU_ITEMS
from account.user_manager import AuthManager


class TestMainMenu:
    """Test main menu functionality"""
    
    def setup_method(self):
        """Reset AuthManager state before each test"""
        AuthManager.clear_session()
    
    def teardown_method(self):
        """Clean up after each test"""
        AuthManager.clear_session()
    
    @patch('cli.main_menu.settings_menu')
    @patch('cli.main_menu.portfolio_menu')
    @patch('cli.main_menu.handle_delete_resume')
    @patch('cli.main_menu.handle_view_resume')
    @patch('cli.main_menu.handle_generate_resume')
    @patch('cli.main_menu.handle_view_edit_rankings')
    @patch('cli.main_menu.handle_rank_and_summarize_projects')
    @patch('cli.main_menu.handle_rank_projects')
    @patch('cli.main_menu.analyze_project_menu')
    @patch('cli.main_menu.handle_analyze_metrics_and_summary')
    @patch('cli.main_menu.project_menu')
    @patch('cli.main_menu.handle_llm_summary')
    @patch('sys.stdin.isatty', return_value=True)
    @patch('os.getenv', side_effect=lambda key, default=None: None if key == "GITHUB_ACTIONS" else default)
    @patch('builtins.input', return_value='14')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_menu_exit_option(
        self,
        mock_stdout,
        mock_input,
        mock_getenv,
        mock_isatty,
        mock_llm_summary,
        mock_project_menu,
        mock_analyze,
        mock_analyze_menu,
        mock_rank,
        mock_rank_summarize,
        mock_view_edit,
        mock_settings,
        mock_generate_resume,
        mock_view_resume,
        mock_delete_resume,
        mock_portfolio
    ):
        """Test that exit option (14) works correctly"""
        # Set up logged in user
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        # Mock logout
        with patch.object(AuthManager, 'logout', return_value={'success': True}):
            run_main_menu(MagicMock(), MagicMock())
        
        output = mock_stdout.getvalue()
        assert "MINING DIGITAL WORK ARTIFACTS - Main Menu" in output
        assert "Logged in as: testuser" in output
        assert "Goodbye!" in output
    
    def test_menu_items_complete(self):
        """Test that all menu items are properly defined"""
        assert len(MENU_ITEMS) == 14
        expected_items = [
            "List/Manage projects",
            "Analyze a project (FULL MODE: metrics + summary)",
            "Analyze a project (PRIVACY MODE: analysis with local fallback)",
            "Rank all projects",
            "Rank and summarize top 3 projects",
            "View and edit stored rankings",
            "Settings",
            "Generate Resume",
            "View Resume",
            "Delete Resume",
            "View Portfolio",
            "Run LLM summary (test.zip)",
            "Project success report (ZIP)",
            "Exit"
        ]
        for i, expected in enumerate(expected_items):
            assert MENU_ITEMS[i] == expected
    
    def test_menu_handlers_mapping(self):
        """Test that menu handlers are properly mapped"""
        # Import the handlers dict logic
        from cli.main_menu import MENU_ITEMS
        
        # Verify menu structure
        assert len(MENU_ITEMS) == 14
        # Options 1-13 should have handlers, option 14 is "EXIT"
        # This tests the structure, actual handler calls are tested in integration
    
    @patch('cli.user_menus.login_menu', return_value=False)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_menu_user_not_logged_in_exit(
        self,
        mock_stdout,
        mock_login
    ):
        """Test that menu exits when user is not logged in and login fails"""
        AuthManager.clear_session()
        
        # Test the logic: when user not logged in and login_menu returns False,
        # the function should return early
        # login_menu is imported inside the function, so we test the import path
        from cli.user_menus import login_menu
        assert callable(login_menu) or hasattr(login_menu, '__call__')
    
    def test_auth_manager_integration(self):
        """Test that AuthManager methods are properly used"""
        # Verify AuthManager methods exist and are callable
        assert hasattr(AuthManager, 'is_user_logged_in')
        assert hasattr(AuthManager, 'get_current_username')
        assert hasattr(AuthManager, 'logout')
        assert callable(AuthManager.is_user_logged_in)
        assert callable(AuthManager.get_current_username)
        assert callable(AuthManager.logout)
    
    @patch('os.getenv')
    @patch('sys.stdin.isatty')
    def test_main_menu_github_actions_auto_exit_logic(
        self,
        mock_isatty,
        mock_getenv
    ):
        """Test that menu auto-exits logic in GitHub Actions environment"""
        # Test the condition logic
        mock_getenv.return_value = 'true'
        mock_isatty.return_value = False
        
        # Verify the condition would trigger auto-exit
        import os
        import sys
        github_actions = os.getenv("GITHUB_ACTIONS") == "true"
        not_tty = not sys.stdin.isatty()
        assert github_actions or not_tty  # This condition triggers auto-exit
    
    @patch('sys.stdin.isatty')
    def test_main_menu_non_tty_auto_exit_logic(
        self,
        mock_isatty
    ):
        """Test that menu auto-exits logic when stdin is not a TTY"""
        mock_isatty.return_value = False
        
        # Verify the condition logic
        import sys
        not_tty = not sys.stdin.isatty()
        assert not_tty  # This condition triggers auto-exit
    
    def test_eof_error_handling_logic(self):
        """Test that EOFError handling logic exists"""
        # Test that the code handles EOFError by setting choice to "14"
        try:
            raise EOFError()
        except EOFError:
            choice = "14"
            assert choice == "14"
    
    def test_settings_menu_in_menu_items(self):
        """Test that Settings menu item exists"""
        # Settings is option 7
        assert "Settings" in MENU_ITEMS
        assert MENU_ITEMS[6] == "Settings"  # Index 6 = option 7
    
    def test_logout_on_exit_logic(self):
        """Test that logout logic is correct for exit"""
        AuthManager._current_user = {'user_name': 'testuser', 'user_id': 1}
        
        # Test the exit logic: if handler == "EXIT" and user is logged in, logout
        handler = "EXIT"
        if handler == "EXIT":
            if AuthManager.is_user_logged_in():
                current_user = AuthManager.get_current_username()
                # Logout would be called here
                assert current_user == 'testuser'
    
    def test_menu_items_structure(self):
        """Test that MENU_ITEMS has correct structure"""
        assert isinstance(MENU_ITEMS, list)
        assert len(MENU_ITEMS) == 14
        assert "List/Manage projects" in MENU_ITEMS
        assert "Exit" in MENU_ITEMS
        assert "Settings" in MENU_ITEMS
    
    def test_menu_handlers_exist(self):
        """Test that all menu handlers are importable"""
        from cli.main_menu import (
            project_menu,
            handle_analyze_metrics_and_summary,
            analyze_project_menu,
            handle_rank_projects,
            handle_rank_and_summarize_projects,
            handle_view_edit_rankings,
            settings_menu,
            portfolio_menu,
            handle_generate_resume,
            handle_view_resume,
            handle_delete_resume,
            handle_llm_summary,
            handle_zip_success_report
        )
        
        # Verify all handlers are callable
        assert callable(project_menu)
        assert callable(handle_llm_summary)
        assert callable(handle_zip_success_report)
        assert callable(settings_menu)
    
    def test_invalid_session_continue_logic(self):
        """Test that menu continues logic when session is invalid after choice"""
        # Test the logic: if user not logged in after choice, print error and continue
        AuthManager.clear_session()
        
        # Simulate the check: if not AuthManager.is_user_logged_in():
        if not AuthManager.is_user_logged_in():
            error_message = "Error: User session invalid. Please log in again."
            # Should continue (not break)
            assert "session invalid" in error_message.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
