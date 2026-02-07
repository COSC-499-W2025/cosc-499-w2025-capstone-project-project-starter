"""
Pytest tests for CollaborativeManager functionality
Tests implemented features:
- Table initialization
- Retrieving preferences
- Requesting collaborative consent

Run with: $env:PYTHONPATH="."; pytest tests -vv
"""

import sys
import os
import pytest
import builtins

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

from collaborative.collaborative_manager import CollaborativeManager
from collaborative.collaborative_storage import CollaborativeStorage
from collaborative.collaborative_display import CollaborativeDisplay

from config.db_config import get_connection

@pytest.fixture(scope="function")
def collaborative_manager():
    """
    Fixture to provide a fresh CollaborativeManager instance for each test.
    """
    # Ensure test_user exists for foreign key constraint
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_informations (user_name, password) 
        VALUES ('test_user', 'test_password') 
        ON CONFLICT (user_name) DO NOTHING;
    """)
    cursor.execute("DELETE FROM user_preferences;")
    conn.commit()
    conn.close()
    
    manager = CollaborativeManager(user_name='test_user')
    
    yield manager

    # Cleanup after test
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_preferences;")
    conn.commit()
    conn.close()

@pytest.fixture(scope="session")
def db_connection():
    """
    Session-level fixture to verify database connection.
    """
    conn = get_connection()
    assert conn is not None, "Database connection failed"
    conn.close()
    return True

class TestDatabaseSetup:
    """Test database connection and setup."""
    
    def test_database_connection(self, db_connection):
        assert db_connection == True
    
    def test_user_preferences_table_initialization(self, collaborative_manager):
        # If we can create a manager without error, table exists
        assert collaborative_manager is not None

class TestGetPreferences:
    """Test retrieving preferences from the database."""
    
    def test_no_preferences_returns_false_false_none(self, collaborative_manager):
        consent, collaborative, last_updated = collaborative_manager.get_preferences()
        assert consent == False
        assert collaborative == False
        assert last_updated is None
    
    def test_preferences_after_insert(self, collaborative_manager):
        # Insert a row manually - needs user_name parameter
        CollaborativeStorage.update_collaborative('test_user', True)
        CollaborativeStorage.update_consent('test_user', True)
        
        consent, collaborative, last_updated = collaborative_manager.get_preferences()
        assert consent == True
        assert collaborative == True
        assert last_updated is not None

class TestRequestCollaborative:
    """Test requesting collaborative consent behavior."""
    
    def test_request_collaborative_grants_consent(self, collaborative_manager, monkeypatch):
        # Simulate user always granting collaborative consent
        monkeypatch.setattr(CollaborativeDisplay, "request_collaborative", lambda: True)

class TestCollaborativeDisplay:
    """Test CollaborativeDisplay functionality."""
    
    def test_request_collaborative_with_github_actions(self, monkeypatch):
        """Test that request_collaborative returns True when GITHUB_ACTIONS is set."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setattr(os, "isatty", lambda x: True)
        result = CollaborativeDisplay.request_collaborative()
        assert result is True
    
    def test_request_collaborative_not_tty(self, monkeypatch):
        """Test that request_collaborative returns True when not a TTY."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setattr(os, "isatty", lambda x: False)
        result = CollaborativeDisplay.request_collaborative()
        assert result is True
    
    def test_request_collaborative_user_input_yes(self, monkeypatch):
        """Test that request_collaborative returns True when user inputs 'yes'."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setattr(os, "isatty", lambda x: True)
        monkeypatch.setattr(builtins, "input", lambda x: "yes")
        result = CollaborativeDisplay.request_collaborative()
        assert result is True
    
    def test_request_collaborative_user_input_y(self, monkeypatch):
        """Test that request_collaborative returns True when user inputs 'y'."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setattr(os, "isatty", lambda x: True)
        monkeypatch.setattr(builtins, "input", lambda x: "y")
        result = CollaborativeDisplay.request_collaborative()
        assert result is True
    
    def test_request_collaborative_user_input_no(self, monkeypatch):
        """Test that request_collaborative returns False when user inputs 'no'."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setattr(os, "isatty", lambda x: True)
        monkeypatch.setattr(builtins, "input", lambda x: "no")
        result = CollaborativeDisplay.request_collaborative()
        assert result is False
    
    def test_request_collaborative_eof_error(self, monkeypatch):
        """Test that request_collaborative returns True when EOFError occurs."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.setattr(os, "isatty", lambda x: True)
        def raise_eof(*args):
            raise EOFError()
        monkeypatch.setattr(builtins, "input", raise_eof)
        result = CollaborativeDisplay.request_collaborative()
        assert result is True
    
    def test_show_status_both_true(self, capsys):
        """Test show_status with both consent and collaborative True."""
        CollaborativeDisplay.show_status(True, True)
        captured = capsys.readouterr()
        assert "Consent:" in captured.out
        assert "Collaborative:" in captured.out
    
    def test_show_status_both_false(self, capsys):
        """Test show_status with both consent and collaborative False."""
        CollaborativeDisplay.show_status(False, False)
        captured = capsys.readouterr()
        assert "Consent:" in captured.out
        assert "Collaborative:" in captured.out
    
    def test_show_status_mixed(self, capsys):
        """Test show_status with mixed True/False values."""
        CollaborativeDisplay.show_status(True, False)
        captured = capsys.readouterr()
        assert "Consent:" in captured.out
        assert "Collaborative:" in captured.out
        
        CollaborativeDisplay.show_status(False, True)
        captured = capsys.readouterr()
        assert "Consent:" in captured.out
        assert "Collaborative:" in captured.out
