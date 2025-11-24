"""
Tests for resume CLI menu handlers
Tests the user-facing resume generation, viewing, and deletion functionality
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call
from io import StringIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestHandleGenerateResume:
    """Test suite for handle_generate_resume function"""
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_generate_resume_new(self, mock_input, mock_resume_manager_class):
        """Test generating a new resume when none exists"""
        from cli.menus import handle_generate_resume
        
        # Mock that no resume exists
        mock_resume_manager_class.resume_exists.return_value = False
        
        # Mock user inputs: top_count = 5 (default), then Enter to continue
        mock_input.side_effect = ['', '']
        
        # Mock successful generation
        mock_resume_data = {
            'total_projects_analyzed': 10,
            'top_projects_displayed': 5,
            'all_skills': ['Python', 'JavaScript', 'Docker']
        }
        mock_resume_manager_class.generate_user_resume.return_value = mock_resume_data
        mock_resume_manager_class.store_user_resume.return_value = True
        
        # Execute
        handle_generate_resume()
        
        # Verify calls
        mock_resume_manager_class.resume_exists.assert_called_once_with("default_user")
        mock_resume_manager_class.generate_user_resume.assert_called_once_with("default_user", top_projects_count=5)
        mock_resume_manager_class.store_user_resume.assert_called_once_with("default_user", mock_resume_data)
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_generate_resume_regenerate_confirmed(self, mock_input, mock_resume_manager_class):
        """Test regenerating resume when user confirms"""
        from cli.menus import handle_generate_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock user inputs: yes to regenerate, 3 top projects, Enter to continue
        mock_input.side_effect = ['yes', '3', '']
        
        # Mock successful generation
        mock_resume_data = {
            'total_projects_analyzed': 10,
            'top_projects_displayed': 3,
            'all_skills': ['Python']
        }
        mock_resume_manager_class.generate_user_resume.return_value = mock_resume_data
        mock_resume_manager_class.store_user_resume.return_value = True
        
        # Execute
        handle_generate_resume()
        
        # Verify regeneration happened
        mock_resume_manager_class.generate_user_resume.assert_called_once_with("default_user", top_projects_count=3)
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_generate_resume_cancel_regenerate(self, mock_input, mock_resume_manager_class):
        """Test cancelling regeneration when resume exists"""
        from cli.menus import handle_generate_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock user input: no to regenerate
        mock_input.return_value = 'no'
        
        # Execute
        handle_generate_resume()
        
        # Verify generation was not called
        mock_resume_manager_class.generate_user_resume.assert_not_called()
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_generate_resume_invalid_then_valid_count(self, mock_input, mock_resume_manager_class):
        """Test handling invalid project count input"""
        from cli.menus import handle_generate_resume
        
        # Mock that no resume exists
        mock_resume_manager_class.resume_exists.return_value = False
        
        # Mock user inputs: invalid count, then valid count, then Enter
        mock_input.side_effect = ['0', '11', 'abc', '7', '']
        
        # Mock successful generation
        mock_resume_data = {
            'total_projects_analyzed': 10,
            'top_projects_displayed': 7,
            'all_skills': []
        }
        mock_resume_manager_class.generate_user_resume.return_value = mock_resume_data
        mock_resume_manager_class.store_user_resume.return_value = True
        
        # Execute
        handle_generate_resume()
        
        # Verify correct count was used
        mock_resume_manager_class.generate_user_resume.assert_called_once_with("default_user", top_projects_count=7)
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_generate_resume_no_projects(self, mock_input, mock_resume_manager_class):
        """Test handling when no projects exist"""
        from cli.menus import handle_generate_resume
        
        # Mock that no resume exists
        mock_resume_manager_class.resume_exists.return_value = False
        
        # Mock user inputs
        mock_input.side_effect = ['', '']
        
        # Mock failed generation (no projects)
        mock_resume_manager_class.generate_user_resume.return_value = None
        
        # Execute
        handle_generate_resume()
        
        # Verify store was not called
        mock_resume_manager_class.store_user_resume.assert_not_called()


class TestHandleViewResume:
    """Test suite for handle_view_resume function"""
    
    @patch('resume.resume_formatter.ResumeFormatter')
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_view_resume_text_format(self, mock_input, mock_resume_manager_class, mock_formatter_class):
        """Test viewing resume in text format"""
        from cli.menus import handle_view_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock resume data
        mock_resume_data = {'user_id': 'default_user', 'all_skills': ['Python']}
        mock_resume_manager_class.get_user_resume.return_value = {
            'resume_data': mock_resume_data
        }
        
        # Mock user input: format choice 1 (text), then Enter
        mock_input.side_effect = ['1', '']
        
        # Mock formatted output
        mock_formatter_class.get_formatted_resume.return_value = "Formatted resume text"
        
        # Execute
        handle_view_resume()
        
        # Verify formatter was called with correct format
        mock_formatter_class.get_formatted_resume.assert_called_once_with(mock_resume_data, 'text')
    
    @patch('resume.resume_formatter.ResumeFormatter')
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_view_resume_markdown_format(self, mock_input, mock_resume_manager_class, mock_formatter_class):
        """Test viewing resume in markdown format"""
        from cli.menus import handle_view_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock resume data
        mock_resume_data = {'user_id': 'default_user'}
        mock_resume_manager_class.get_user_resume.return_value = {
            'resume_data': mock_resume_data
        }
        
        # Mock user input: format choice 2 (markdown)
        mock_input.side_effect = ['2', '']
        
        # Mock formatted output
        mock_formatter_class.get_formatted_resume.return_value = "# Resume"
        
        # Execute
        handle_view_resume()
        
        # Verify formatter was called with markdown format
        mock_formatter_class.get_formatted_resume.assert_called_once_with(mock_resume_data, 'markdown')
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_view_resume_not_found(self, mock_input, mock_resume_manager_class):
        """Test viewing resume when none exists"""
        from cli.menus import handle_view_resume
        
        # Mock that no resume exists
        mock_resume_manager_class.resume_exists.return_value = False
        
        # Mock user input
        mock_input.return_value = ''
        
        # Execute
        handle_view_resume()
        
        # Verify get_user_resume was not called
        mock_resume_manager_class.get_user_resume.assert_not_called()


class TestHandleDeleteResume:
    """Test suite for handle_delete_resume function"""
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_delete_resume_confirmed(self, mock_input, mock_resume_manager_class):
        """Test deleting resume when user confirms"""
        from cli.menus import handle_delete_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock user inputs: yes to confirm, then Enter
        mock_input.side_effect = ['yes', '']
        
        # Mock successful deletion
        mock_resume_manager_class.delete_user_resume.return_value = True
        
        # Execute
        handle_delete_resume()
        
        # Verify deletion was called
        mock_resume_manager_class.delete_user_resume.assert_called_once_with("default_user")
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_delete_resume_cancelled(self, mock_input, mock_resume_manager_class):
        """Test cancelling resume deletion"""
        from cli.menus import handle_delete_resume
        
        # Mock that resume exists
        mock_resume_manager_class.resume_exists.return_value = True
        
        # Mock user inputs: no to confirm, then Enter
        mock_input.side_effect = ['no', '']
        
        # Execute
        handle_delete_resume()
        
        # Verify deletion was not called
        mock_resume_manager_class.delete_user_resume.assert_not_called()
    
    @patch('resume.resume_manager.ResumeManager')
    @patch('builtins.input')
    def test_delete_resume_not_found(self, mock_input, mock_resume_manager_class):
        """Test deleting resume when none exists"""
        from cli.menus import handle_delete_resume
        
        # Mock that no resume exists
        mock_resume_manager_class.resume_exists.return_value = False
        
        # Mock user input
        mock_input.return_value = ''
        
        # Execute
        handle_delete_resume()
        
        # Verify delete was not called
        mock_resume_manager_class.delete_user_resume.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])