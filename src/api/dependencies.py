"""Shared dependencies for API routes."""
from config.db_config import get_connection
from typing import Generator

def get_db_cursor() -> Generator:
    """
    FastAPI dependency for database cursor.
    FastAPI manages the lifecycle - code after yield runs as cleanup.
    """
    conn = get_connection()
    if not conn:
        raise ConnectionError("Could not connect to database")
    
    cursor = None
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        conn.close()

def check_db_connection() -> bool:
    """Check if database connection is available."""
    conn = get_connection()
    if conn:
        conn.close()
        return True
    return False
