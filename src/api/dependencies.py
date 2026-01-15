"""Shared dependencies for API routes."""
from config.db_config import with_db_cursor, get_connection
from typing import Generator
from contextlib import contextmanager

@contextmanager
def get_db_cursor():
    """Dependency for database cursor in routes."""
    with with_db_cursor() as cursor:
        yield cursor

def check_db_connection() -> bool:
    """Check if database connection is available."""
    conn = get_connection()
    if conn:
        conn.close()
        return True
    return False
