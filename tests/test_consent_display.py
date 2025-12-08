"""
Comprehensive tests for ConsentDisplay class to improve test coverage.
Tests both show_consent_message and prompt_for_consent methods.
"""

import sys
import os
from unittest.mock import patch, MagicMock
import io
from contextlib import redirect_stdout

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

import pytest
from consent.consent_display import ConsentDisplay


class TestConsentDisplayShowMessage:
    """Tests for the show_consent_message method."""
    
    def test_show_consent_message_output_structure(self):
        """Test that consent message has proper structure and formatting."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        # Test basic structure
        assert "DATA ACCESS CONSENT REQUEST" in output
        assert "╔" in output and "╗" in output and "║" in output  # Box drawing characters
        assert "┌" in output and "┐" in output and "└" in output and "┘" in output  # Box drawing characters
        
    def test_show_consent_message_contains_all_sections(self):
        """Test that all required consent sections are present."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        # Test all main sections
        required_sections = [
            "WHAT DATA WILL BE ACCESSED",
            "HOW YOUR DATA WILL BE USED", 
            "DATA STORAGE & RETENTION",
            "YOUR RIGHTS"
        ]
        
        for section in required_sections:
            assert section in output, f"Missing required section: {section}"
    
    def test_show_consent_message_data_types(self):
        """Test that specific data types are mentioned."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        data_types = [
            "File metadata",
            "File contents",
            "Programming code",
            "repositories",
            "Written documents",
            "Design files",
            "Git commit history"
        ]
        
        for data_type in data_types:
            assert data_type in output, f"Missing data type: {data_type}"
    
    def test_show_consent_message_usage_purposes(self):
        """Test that data usage purposes are clearly stated."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        purposes = [
            "Analyze project structure",
            "Extract contribution metrics",
            "programming languages, frameworks",
            "collaborative work",
            "portfolio summaries",
            "local database"
        ]
        
        for purpose in purposes:
            assert purpose in output, f"Missing usage purpose: {purpose}"
    
    def test_show_consent_message_storage_info(self):
        """Test that storage and retention information is included."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        storage_info = [
            "Duration:",
            "Location:",
            "Security:",
            "External Services:",
            "Local PostgreSQL database",
            "local machine"
        ]
        
        for info in storage_info:
            assert info in output, f"Missing storage info: {info}"
    
    def test_show_consent_message_user_rights(self):
        """Test that user rights are clearly stated."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        rights = [
            "withdraw consent",
            "delete all stored insights",
            "control what folders"
        ]
        
        for right in rights:
            assert right in output, f"Missing user right: {right}"
    
    def test_show_consent_message_important_notice(self):
        """Test that important notice and warnings are included."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        assert "IMPORTANT" in output
        assert "providing consent" in output
        assert "acknowledge" in output


class TestConsentDisplayPromptForConsent:
    """Tests for the prompt_for_consent method."""
    
    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    def test_prompt_for_consent_github_actions_environment(self):
        """Test that consent is auto-granted in GitHub Actions environment."""
        result = ConsentDisplay.prompt_for_consent()
        assert result is True
    
    @patch('os.getenv')
    @patch('os.isatty')
    def test_prompt_for_consent_non_interactive_terminal(self, mock_isatty, mock_getenv):
        """Test that consent is auto-granted in non-interactive environment."""
        mock_getenv.return_value = None  # Not GitHub Actions
        mock_isatty.return_value = False  # Non-interactive terminal
        
        result = ConsentDisplay.prompt_for_consent()
        assert result is True
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_yes_response(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test consent granted with 'yes' response."""
        mock_getenv.return_value = None  # Not GitHub Actions
        mock_isatty.return_value = True  # Interactive terminal
        mock_input.return_value = "yes"
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is True
        mock_print.assert_called_with("\nConsent granted. Thank you!")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_y_response(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test consent granted with 'y' response."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.return_value = "y"
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is True
        mock_print.assert_called_with("\nConsent granted. Thank you!")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_no_response(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test consent denied with 'no' response."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.return_value = "no"
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is False
        mock_print.assert_called_with("\nConsent denied. The application cannot proceed without consent.")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_n_response(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test consent denied with 'n' response."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.return_value = "n"
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is False
        mock_print.assert_called_with("\nConsent denied. The application cannot proceed without consent.")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_invalid_then_yes(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test handling of invalid input followed by valid 'yes'."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.side_effect = ["invalid", "yes"]
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is True
        # Check that error message was printed for invalid input
        mock_print.assert_any_call("Invalid input. Please enter 'yes' or 'no'.")
        mock_print.assert_any_call("\nConsent granted. Thank you!")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_invalid_then_no(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test handling of invalid input followed by valid 'no'."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.side_effect = ["maybe", "no"]
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is False
        mock_print.assert_any_call("Invalid input. Please enter 'yes' or 'no'.")
        mock_print.assert_any_call("\nConsent denied. The application cannot proceed without consent.")
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_for_consent_multiple_invalid_inputs(self, mock_print, mock_input, mock_isatty, mock_getenv):
        """Test handling of multiple invalid inputs before valid response."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.side_effect = ["invalid", "wrong", "bad", "yes"]
        
        result = ConsentDisplay.prompt_for_consent()
        
        assert result is True
        # Should have printed invalid input message 3 times
        invalid_calls = [call for call in mock_print.call_args_list 
                        if "Invalid input" in str(call)]
        assert len(invalid_calls) == 3
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    def test_prompt_for_consent_case_insensitive(self, mock_input, mock_isatty, mock_getenv):
        """Test that responses are case-insensitive."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        
        # Test various cases
        test_cases = [
            ("YES", True),
            ("Yes", True),
            ("Y", True),
            ("NO", False),
            ("No", False),
            ("N", False)
        ]
        
        for input_value, expected in test_cases:
            mock_input.return_value = input_value
            result = ConsentDisplay.prompt_for_consent()
            assert result == expected, f"Failed for input: {input_value}"
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    def test_prompt_for_consent_whitespace_handling(self, mock_input, mock_isatty, mock_getenv):
        """Test that whitespace is properly stripped from input."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        
        # Test with whitespace
        test_cases = [
            ("  yes  ", True),
            ("\tno\t", False),
            (" Y ", True),
            ("\nN\n", False)
        ]
        
        for input_value, expected in test_cases:
            mock_input.return_value = input_value
            result = ConsentDisplay.prompt_for_consent()
            assert result == expected, f"Failed for input: '{input_value}'"
    
    @patch('os.getenv')
    @patch('os.isatty')
    @patch('builtins.input')
    def test_prompt_for_consent_eof_error_handling(self, mock_input, mock_isatty, mock_getenv):
        """Test handling of EOFError (Ctrl+D)."""
        mock_getenv.return_value = None
        mock_isatty.return_value = True
        mock_input.side_effect = EOFError()
        
        result = ConsentDisplay.prompt_for_consent()
        
        # Should return True on EOFError (as per the code)
        assert result is True


class TestConsentDisplayEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_show_consent_message_no_exceptions(self):
        """Test that show_consent_message doesn't raise any exceptions."""
        try:
            ConsentDisplay.show_consent_message()
        except Exception as e:
            pytest.fail(f"show_consent_message raised an unexpected exception: {e}")
    
    @patch('builtins.print')
    def test_show_consent_message_calls_print(self, mock_print):
        """Test that show_consent_message actually calls print function."""
        ConsentDisplay.show_consent_message()
        
        # Verify print was called at least once
        assert mock_print.called
        
        # Verify the content passed to print contains consent text
        call_args = mock_print.call_args[0][0]
        assert "DATA ACCESS CONSENT REQUEST" in call_args


class TestConsentDisplayIntegration:
    """Integration tests for the ConsentDisplay class."""
    
    def test_consent_message_length(self):
        """Test that consent message is substantial and not too short."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        # Should be a substantial message (at least 1000 characters)
        assert len(output) > 1000, "Consent message is too short"
    
    def test_consent_message_readability(self):
        """Test that consent message contains readable text, not just formatting."""
        f = io.StringIO()
        with redirect_stdout(f):
            ConsentDisplay.show_consent_message()
        output = f.getvalue()
        
        # Remove formatting characters and count actual content
        import re
        # Remove box drawing characters and extra whitespace
        clean_text = re.sub(r'[│┌┐└┘─╔╗║╚═╝┤├┬┴┼]', '', output)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Should have substantial readable content
        assert len(clean_text) > 500, "Not enough readable content in consent message"
    
    @patch('os.getenv')
    @patch('os.isatty')  
    @patch('builtins.input')
    def test_realistic_user_interaction_flow(self, mock_input, mock_isatty, mock_getenv):
        """Test a realistic user interaction flow."""
        mock_getenv.return_value = None  # Not GitHub Actions
        mock_isatty.return_value = True   # Interactive terminal
        
        # Simulate user trying different inputs before saying yes
        mock_input.side_effect = ["help", "what", "yes"]
        
        with patch('builtins.print') as mock_print:
            result = ConsentDisplay.prompt_for_consent()
        
        assert result is True
        
        # Verify appropriate responses to invalid input
        print_calls = [str(call) for call in mock_print.call_args_list]
        invalid_messages = [call for call in print_calls if "Invalid input" in call]
        assert len(invalid_messages) == 2  # Should have 2 invalid input messages