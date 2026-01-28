"""Shared dependencies for API routes."""
from fastapi import HTTPException, Query
from config.db_config import get_connection
from typing import Generator, Optional
from database.user_informations import get_user_by_username

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


def get_authenticated_user(
    username: str = Query(..., description="Username of the authenticated user")
) -> dict:
    """
    FastAPI dependency to verify user is authenticated and return user data.
    
    Args:
        username: Username to verify authentication for
        
    Returns:
        dict: User data if authenticated
        
    Raises:
        HTTPException: If user is not found or not logged in
    """
    if not username or not username.strip():
        raise HTTPException(
            status_code=401,
            detail="Username is required for authentication"
        )
    
    user_data = get_user_by_username(username.strip())
    
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    if not user_data.get('is_login', False):
        raise HTTPException(
            status_code=401,
            detail="User is not authenticated. Please log in first."
        )
    
    return user_data
