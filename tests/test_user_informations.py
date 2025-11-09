# tests/test_user_informations.py

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add the project root to sys.path so `config` can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import your module
from database import user_informations

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
    
    with patch('database.user_informations.get_connection', return_value=mock_conn_context):
        yield mock_cursor, mock_conn

# ----------------------------
# Core Function Tests
# ----------------------------

def test_hash_password():
    """Test password hashing functionality."""
    password = "test_password"
    hashed = user_informations.hash_password(password)
    
    # Test basic hash properties
    assert hashed is not None
    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA-256 produces 64-character hex string
    
    # Test consistency and uniqueness
    assert user_informations.hash_password(password) == hashed
    assert user_informations.hash_password("different_password") != hashed

@pytest.mark.parametrize("table_exists", [True, False])
def test_init_user_informations_table(mock_conn_cursor, table_exists):
    """Test table initialization for both scenarios."""
    mock_cursor, mock_conn = mock_conn_cursor
    mock_cursor.fetchone.return_value = (table_exists,)
    
    user_informations.init_user_informations_table()
    
    if table_exists:
        assert mock_cursor.execute.call_count == 1  # Only check existence
        mock_conn.commit.assert_not_called()
    else:
        assert mock_cursor.execute.call_count == 2  # Check + create
        mock_conn.commit.assert_called_once()

def test_create_user(mock_conn_cursor):
    """Test user creation success and failure."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    # Test success
    mock_cursor.fetchone.return_value = (123,)
    result = user_informations.create_user("test_user", "password")
    assert result == 123
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

@pytest.mark.parametrize("user_exists", [True, False])
def test_get_user_by_username(mock_conn_cursor, user_exists):
    """Test getting user by username for both found/not found scenarios."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    if user_exists:
        mock_user_data = (1, "test_user", datetime(2023, 1, 1), datetime(2023, 1, 2), True)
        mock_cursor.fetchone.return_value = mock_user_data
        
        result = user_informations.get_user_by_username("test_user")
        
        assert result is not None
        assert result['user_id'] == 1
        assert result['user_name'] == "test_user"
        assert result['is_login'] == True
    else:
        mock_cursor.fetchone.return_value = None
        
        result = user_informations.get_user_by_username("nonexistent_user")
        assert result is None

@pytest.mark.parametrize("password_correct", [True, False])
def test_verify_password(mock_conn_cursor, password_correct):
    """Test password verification for correct and incorrect passwords."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    if password_correct:
        mock_cursor.fetchone.return_value = (1,)  # User found
        result = user_informations.verify_password("test_user", "correct_password")
        assert result is True
    else:
        mock_cursor.fetchone.return_value = None  # User not found
        result = user_informations.verify_password("test_user", "wrong_password")
        assert result is False

@patch('database.user_informations.verify_password')
def test_login_user(mock_verify_password, mock_conn_cursor):
    """Test user login with both success and failure scenarios."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    # Test successful login
    mock_verify_password.return_value = True
    result = user_informations.login_user("test_user", "correct_password")
    assert result is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    
    # Reset mocks for failure test
    mock_cursor.reset_mock()
    mock_conn.reset_mock()
    
    # Test failed login
    mock_verify_password.return_value = False
    result = user_informations.login_user("test_user", "wrong_password")
    assert result is False
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()

@pytest.mark.parametrize("user_exists", [True, False])
def test_logout_user(mock_conn_cursor, user_exists):
    """Test user logout for existing and non-existing users."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    if user_exists:
        mock_cursor.rowcount = 1  # One row affected
        result = user_informations.logout_user("test_user")
        assert result is True
        mock_conn.commit.assert_called_once()
    else:
        mock_cursor.rowcount = 0  # No rows affected
        result = user_informations.logout_user("nonexistent_user")
        assert result is False
        mock_conn.commit.assert_not_called()

def test_get_all_users(mock_conn_cursor):
    """Test getting all users with data and without data."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    # Test with users
    mock_users_data = [
        (1, "user1", datetime(2023, 1, 1), datetime(2023, 1, 2), True),
        (2, "user2", datetime(2023, 1, 3), None, False)
    ]
    mock_cursor.fetchall.return_value = mock_users_data
    
    result = user_informations.get_all_users()
    assert len(result) == 2
    assert result[0]['user_name'] == "user1"
    assert result[1]['user_name'] == "user2"

def test_get_logged_in_users(mock_conn_cursor):
    """Test getting logged-in users."""
    mock_cursor, mock_conn = mock_conn_cursor
    mock_users_data = [
        (1, "user1", datetime(2023, 1, 1), datetime(2023, 1, 2), True),
        (3, "user3", datetime(2023, 1, 4), datetime(2023, 1, 5), True)
    ]
    mock_cursor.fetchall.return_value = mock_users_data
    
    result = user_informations.get_logged_in_users()
    assert len(result) == 2
    assert all(user['is_login'] for user in result)

@pytest.mark.parametrize("username_available", [True, False])
def test_is_username_available(mock_conn_cursor, username_available):
    """Test username availability check."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    if username_available:
        mock_cursor.fetchone.return_value = None  # Username not found
        result = user_informations.is_username_available("new_user")
        assert result is True
    else:
        mock_cursor.fetchone.return_value = (1,)  # Username found
        result = user_informations.is_username_available("existing_user")
        assert result is False

def test_get_user_count(mock_conn_cursor):
    """Test getting user count."""
    mock_cursor, mock_conn = mock_conn_cursor
    mock_cursor.fetchone.return_value = (5,)
    
    result = user_informations.get_user_count()
    assert result == 5

# ----------------------------
# Error Handling Tests (Consolidated)
# ----------------------------

@pytest.mark.parametrize("function_name,args,expected_return", [
    ("create_user", ("user", "pass"), None),
    ("get_user_by_username", ("user",), None),
    ("verify_password", ("user", "pass"), False),
    ("logout_user", ("user",), False),
    ("get_all_users", (), []),
    ("get_logged_in_users", (), []),
    ("is_username_available", ("user",), False),
    ("get_user_count", (), 0)
])
def test_database_errors(mock_conn_cursor, function_name, args, expected_return):
    """Test database error handling across multiple functions."""
    mock_cursor, mock_conn = mock_conn_cursor
    mock_cursor.execute.side_effect = Exception("Database error")
    
    function = getattr(user_informations, function_name)
    result = function(*args)
    assert result == expected_return

# ----------------------------
# Integration Test (Simplified)
# ----------------------------

def test_user_registration_and_login_workflow(mock_conn_cursor):
    """Test the complete user registration and login workflow."""
    mock_cursor, mock_conn = mock_conn_cursor
    
    # Setup sequential mock responses
    mock_cursor.fetchone.side_effect = [
        None,  # Username available
        (1,),  # User created successfully
        (1, "new_user", datetime.now(), None, False)  # User data retrieved
    ]
    
    # Test workflow
    assert user_informations.is_username_available("new_user") is True
    user_id = user_informations.create_user("new_user", "password123")
    assert user_id == 1
    user_info = user_informations.get_user_by_username("new_user")
    assert user_info['user_name'] == "new_user"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])