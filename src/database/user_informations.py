from config.db_config import get_connection
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib


def init_user_informations_table():
    """
    Create the user_informations table if it does not exist.
    This table stores user account information including login status.
    """
    with get_connection() as conn, conn.cursor() as cur:
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'user_informations'
            );
        """)
        exists = cur.fetchone()[0]

        if not exists:
            # user id is self incremented and immutable
            cur.execute("""
                CREATE TABLE user_informations (
                    user_id SERIAL PRIMARY KEY,
                    user_name VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    create_time TIMESTAMP DEFAULT NOW(),
                    last_login_time TIMESTAMP,
                    is_login BOOLEAN DEFAULT FALSE
                );
            """)
            conn.commit()
            print("user_informations table created successfully.")
        else:
            print("user_informations table already exists.")


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    
    Args:
        password (str): The plain text password
        
    Returns:
        str: The hashed password
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_user(user_name: str, password: str) -> Optional[int]:
    """
    Create a new user account.
    
    Args:
        user_name (str): The username (must be unique)
        password (str): The plain text password
        
    Returns:
        Optional[int]: The user_id of the created user, or None if creation failed
    """
    try:
        hashed_password = hash_password(password)
        
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_informations (user_name, password, create_time, is_login)
                VALUES (%s, %s, NOW(), FALSE)
                RETURNING user_id;
            """, (user_name, hashed_password))
            
            user_id = cur.fetchone()[0]
            conn.commit()
            print(f"User '{user_name}' created successfully with ID: {user_id}")
            return user_id
            
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def get_user_by_username(user_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user information by username.
    
    Args:
        user_name (str): The username
        
    Returns:
        Optional[Dict[str, Any]]: User information dictionary or None if not found
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, user_name, create_time, last_login_time, is_login
                FROM user_informations
                WHERE user_name = %s;
            """, (user_name,))
            
            result = cur.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'user_name': result[1],
                    'create_time': result[2],
                    'last_login_time': result[3],
                    'is_login': result[4]
                }
            return None
            
    except Exception as e:
        print(f"Error retrieving user by username: {e}")
        return None


def verify_password(user_name: str, password: str) -> bool:
    """
    Verify a user's password.
    
    Args:
        user_name (str): The username
        password (str): The plain text password
        
    Returns:
        bool: True if password is correct, False otherwise
    """
    try:
        hashed_password = hash_password(password)
        
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT user_id FROM user_informations
                WHERE user_name = %s AND password = %s;
            """, (user_name, hashed_password))
            
            return cur.fetchone() is not None
            
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def login_user(user_name: str, password: str) -> bool:
    """
    Log in a user by verifying password and updating login status.
    
    Args:
        user_name (str): The username
        password (str): The plain text password
        
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        if verify_password(user_name, password):
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_informations
                    SET last_login_time = NOW(), is_login = TRUE
                    WHERE user_name = %s;
                """, (user_name,))
                conn.commit()
                print(f"User '{user_name}' logged in successfully.")
                return True
        else:
            print("Invalid username or password.")
            return False
            
    except Exception as e:
        print(f"Error during login: {e}")
        return False


def logout_user(user_name: str) -> bool:
    """
    Log out a user by updating login status.
    
    Args:
        user_name (str): The username
        
    Returns:
        bool: True if logout successful, False otherwise
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE user_informations
                SET is_login = FALSE
                WHERE user_name = %s;
            """, (user_name,))
            
            if cur.rowcount > 0:
                conn.commit()
                print(f"User '{user_name}' logged out successfully.")
                return True
            else:
                print(f"User '{user_name}' not found.")
                return False
                
    except Exception as e:
        print(f"Error during logout: {e}")
        return False


def get_all_users() -> List[Dict[str, Any]]:
    """
    Retrieve all users (without password information).
    
    Returns:
        List[Dict[str, Any]]: List of user information dictionaries
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, user_name, create_time, last_login_time, is_login
                FROM user_informations
                ORDER BY user_id;
            """)
            
            results = cur.fetchall()
            users = []
            for result in results:
                users.append({
                    'user_id': result[0],
                    'user_name': result[1],
                    'create_time': result[2],
                    'last_login_time': result[3],
                    'is_login': result[4]
                })
            return users
            
    except Exception as e:
        print(f"Error retrieving all users: {e}")
        return []


def get_logged_in_users() -> List[Dict[str, Any]]:
    """
    Retrieve all currently logged-in users.
    
    Returns:
        List[Dict[str, Any]]: List of logged-in user information dictionaries
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, user_name, create_time, last_login_time, is_login
                FROM user_informations
                WHERE is_login = TRUE
                ORDER BY last_login_time DESC;
            """)
            
            results = cur.fetchall()
            users = []
            for result in results:
                users.append({
                    'user_id': result[0],
                    'user_name': result[1],
                    'create_time': result[2],
                    'last_login_time': result[3],
                    'is_login': result[4]
                })
            return users
            
    except Exception as e:
        print(f"Error retrieving logged-in users: {e}")
        return []


def is_username_available(user_name: str) -> bool:
    """
    Check if a username is available (not already taken).
    
    Args:
        user_name (str): The username to check
        
    Returns:
        bool: True if username is available, False if taken
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT user_id FROM user_informations
                WHERE user_name = %s;
            """, (user_name,))
            
            return cur.fetchone() is None
            
    except Exception as e:
        print(f"Error checking username availability: {e}")
        return False


def get_user_count() -> int:
    """
    Get the total number of registered users.
    
    Returns:
        int: Total number of users
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_informations;")
            return cur.fetchone()[0]
            
    except Exception as e:
        print(f"Error getting user count: {e}")
        return 0
