"""
test_LLM_permission.py

Unit tests for LLM_permission.py.
Covers:
 - Consent handling
 - Fallback to local analysis
 - External vs local analysis branching
"""

from unittest.mock import patch
from src.validator.LLM_permission import (
    request_consent,
    process_data_with_permission,
    analyze_with_external_service,
    analyze_locally
)

def test_permission_granted():
    """Test that consent returns True when user inputs 'yes'."""
    with patch("builtins.input", return_value="yes"):
        result = request_consent()
        assert result is True

def test_permission_denied():
    """Test that consent returns False when user inputs 'no'."""
    with patch("builtins.input", return_value="no"):
        result = request_consent()
        assert result is True

def test_invalid_input_then_valid():
    """Test that invalid input is handled and reprompted until valid input is given."""
    with patch("builtins.input", side_effect=["maybe", "YES"]):
        result = request_consent()
        assert result is True

def test_process_data_with_permission_external(monkeypatch):
    """Test that data goes to external service if user consents."""
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    monkeypatch.setattr("src.validator.LLM_permission.run_ollama_analysis", lambda prompt: "EXTERNAL")
    result = process_data_with_permission("TestService", "source code", "dummy")
    assert result == "EXTERNAL"

def test_process_data_with_permission_local(monkeypatch):
    """Test that data goes to local analysis if user declines."""
    # Ensure tests ignore stored config
    import src.validator.LLM_permission as llm
    llm.IS_TESTING = True

    monkeypatch.setattr("builtins.input", lambda _: "no")
    monkeypatch.setattr("src.validator.LLM_permission.analyze_locally", lambda data: "LOCAL")
    result = llm.process_data_with_permission("TestService", "source code", "dummy")
    assert result == "LOCAL"

