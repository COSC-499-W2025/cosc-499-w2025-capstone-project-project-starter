import os
import sys
from unittest.mock import MagicMock, patch
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from external_services.service_config import ServiceConfig  # noqa: E402


def _ctx_with_cursor(cursor):
    """Helper to mock the context manager for database cursors."""
    ctx = MagicMock()
    ctx.__enter__.return_value = cursor
    ctx.__exit__.return_value = False
    return ctx


@patch("external_services.service_config.with_db_cursor")
def test_initialize_table_success(mock_cursor_factory):
    """Ensure initialize_table executes the correct creation statements."""
    cursor = MagicMock()
    mock_cursor_factory.return_value = _ctx_with_cursor(cursor)

    ServiceConfig.initialize_table()

    # Verify table creation and index creation were called
    assert cursor.execute.call_count == 2
    
    # Check for specific SQL snippets to ensure correct queries
    calls = [args[0] for args, _ in cursor.execute.call_args_list]
    assert "CREATE TABLE IF NOT EXISTS external_service_permissions" in calls[0]
    # Check for user_name column (not user_id) and foreign key
    assert "user_name" in calls[0].lower()
    assert "CREATE INDEX IF NOT EXISTS idx_service_permissions_user_service" in calls[1]


@patch("external_services.service_config.with_db_cursor")
def test_initialize_table_connection_error(mock_cursor_factory):
    """Ensure initialize_table raises Exception on DB connection failure."""
    mock_cursor_factory.side_effect = ConnectionError("DB is down")

    with pytest.raises(Exception) as excinfo:
        ServiceConfig.initialize_table()
    
    assert "Failed to connect to database" in str(excinfo.value)


@patch("external_services.service_config.with_db_cursor")
def test_get_permission_granted(mock_cursor_factory):
    """Test retrieving a granted permission (True)."""
    cursor = MagicMock()
    # Mock result: (True,)
    cursor.fetchone.return_value = (True,)
    mock_cursor_factory.return_value = _ctx_with_cursor(cursor)

    result = ServiceConfig.get_permission("user123", "LLM")

    assert result is True
    # Verify query parameters
    cursor.execute.assert_called_once()
    args, _ = cursor.execute.call_args
    assert args[1] == ("user123", "LLM")


@patch("external_services.service_config.with_db_cursor")
def test_get_permission_denied(mock_cursor_factory):
    """Test retrieving a denied permission (False)."""
    cursor = MagicMock()
    # Mock result: (False,)
    cursor.fetchone.return_value = (False,)
    mock_cursor_factory.return_value = _ctx_with_cursor(cursor)

    result = ServiceConfig.get_permission("user123", "LLM")

    assert result is False


@patch("external_services.service_config.with_db_cursor")
def test_get_permission_none_found(mock_cursor_factory):
    """Test retrieving permission when no record exists."""
    cursor = MagicMock()
    # Mock result: None (no row found)
    cursor.fetchone.return_value = None
    mock_cursor_factory.return_value = _ctx_with_cursor(cursor)

    result = ServiceConfig.get_permission("user123", "LLM")

    assert result is None


@patch("external_services.service_config.with_db_cursor")
def test_get_permission_db_error_returns_none(mock_cursor_factory):
    """Ensure database errors result in a None return value (safe failure)."""
    mock_cursor_factory.side_effect = Exception("Unexpected DB error")

    # Should not raise exception, but return None per implementation
    result = ServiceConfig.get_permission("user123", "LLM")

    assert result is None