# tests/test_user_preferences.py

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add the project root to sys.path so `config` can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import your module
from database import user_preferences

@pytest.fixture
def mock_conn_cursor():
    """
    Fixture to mock get_connection() and provide a cursor.
    """
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    
    # Setup cursor as context manager - cursor() returns a context manager that yields mock_cursor
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    
    # Setup connection as context manager - get_connection() returns a context manager that yields mock_conn
    mock_conn_context = MagicMock()
    mock_conn_context.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn_context.__exit__ = MagicMock(return_value=False)
    
    with patch('database.user_preferences.get_connection', return_value=mock_conn_context):
        yield mock_cursor, mock_conn

# ----------------------------
# Tests for init_user_preferences_table
# ----------------------------
@pytest.mark.parametrize("exists", [True, False])
def test_init_user_preferences_table_commit_depends(mock_conn_cursor, exists):
    mock_cursor, mock_conn = mock_conn_cursor
    mock_cursor.fetchone.return_value = (exists,)
    user_preferences.init_user_preferences_table()
    if exists:
        mock_conn.commit.assert_not_called()
    else:
        mock_conn.commit.assert_called_once()

# ----------------------------
# Tests for update_user_preferences
# ----------------------------
@pytest.mark.parametrize("consent_val", [True, False])
def test_update_user_preferences(mock_conn_cursor, consent_val):
    mock_cursor, mock_conn = mock_conn_cursor
    user_preferences.update_user_preferences('test_user', consent_val)
    mock_cursor.execute.assert_called()
    args, _ = mock_cursor.execute.call_args
    assert str(consent_val) in str(args)

# ----------------------------
# Tests for get_user_preferences
# ----------------------------
def test_get_user_preferences_returns_tuple(mock_conn_cursor):
    mock_cursor, mock_conn = mock_conn_cursor
    expected = (True, datetime.now())
    mock_cursor.fetchone.return_value = expected
    result = user_preferences.get_user_preferences('test_user')
    assert result == expected

# ----------------------------
# Tests for update_user_collaboration
# ----------------------------
@pytest.mark.parametrize("collab_val", [True, False])
def test_update_user_collaboration(monkeypatch, collab_val):
    # Build the connection context manager
    conn_cm = MagicMock(name="conn_cm")
    conn = MagicMock(name="conn")
    conn_cm.__enter__.return_value = conn
    # Build the cursor context manager
    cursor_cm = MagicMock(name="cursor_cm")
    cursor = MagicMock(name="cursor")
    cursor_cm.__enter__.return_value = cursor
    conn.cursor.return_value = cursor_cm
    # Patch get_connection to return the connection context manager and run
    monkeypatch.setattr(user_preferences, "get_connection", MagicMock(return_value=conn_cm))
    user_preferences.update_user_collaboration('test_user', collab_val)
    # Assert SQL executed with the right parameter
    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert params == ('test_user', collab_val)
    conn.commit.assert_called_once()
    cursor_cm.__exit__.assert_called_once()
    conn_cm.__exit__.assert_called_once()

# ----------------------------
# Tests for get_user_callaboration
# ----------------------------
def test_get_user_callaboration_returns_tuple(mock_conn_cursor):
    mock_cursor, mock_conn = mock_conn_cursor
    expected = (False, datetime.now())
    mock_cursor.fetchone.return_value = expected
    result = user_preferences.get_user_collaboration('test_user')
    assert result == expected

# ----------------------------
# Tests for update_user_git_username
# ----------------------------
def test_update_user_git_username(monkeypatch):
    # Build the connection context manager
    conn_cm = MagicMock(name="conn_cm")
    conn = MagicMock(name="conn")
    conn_cm.__enter__.return_value = conn
    # Build the cursor context manager
    cursor_cm = MagicMock(name="cursor_cm")
    cursor = MagicMock(name="cursor")
    cursor_cm.__enter__.return_value = cursor
    conn.cursor.return_value = cursor_cm
    # Patch get_connection to return the connection context manager and run
    monkeypatch.setattr(user_preferences, "get_connection", MagicMock(return_value=conn_cm))
    username = "testuser"
    user_preferences.update_user_git_username('test_user', username)
    # Assertions
    cursor.execute.assert_called_once()
    args, kwargs = cursor.execute.call_args
    assert username in str(args)  # contains the %s param value
    conn.commit.assert_called_once()
    cursor_cm.__exit__.assert_called_once()
    conn_cm.__exit__.assert_called_once()


# ----------------------------
# Tests for get_user_git_username
# ----------------------------
def test_get_user_git_username_returns_tuple(mock_conn_cursor):
    mock_cursor, mock_conn = mock_conn_cursor
    expected = ("testuser",)
    mock_cursor.fetchone.return_value = expected
    result = user_preferences.get_user_git_username('test_user')
    assert result == "testuser"  # function returns result[0], not the full tuple
