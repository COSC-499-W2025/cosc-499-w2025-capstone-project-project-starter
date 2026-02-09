from config.db_config import get_connection


def init_user_preferences_table():
    """
    Create the user_preferences table if it does not exist.
    This table stores user consent and future preferences.
    Uses user_name as foreign key to user_informations table.
    """
    with get_connection() as conn, conn.cursor() as cur:
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'user_preferences'
            );
        """)
        exists = cur.fetchone()[0]

        if not exists:
            cur.execute("""
                CREATE TABLE user_preferences (
                    user_name VARCHAR(255) PRIMARY KEY,
                    consent BOOLEAN DEFAULT FALSE,
                    collaborative BOOLEAN DEFAULT FALSE,
                    git_username VARCHAR(255),
                    last_updated TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_name) REFERENCES user_informations(user_name) ON DELETE CASCADE
                );
            """)
            conn.commit()


def update_user_preferences(user_name: str, consent: bool):
    """
    Update the user's consent preference in the database.
    If the record doesn't exist, insert it.
    
    Args:
        user_name: The username from user_informations table
        consent: The consent preference value
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, consent, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET consent = EXCLUDED.consent, last_updated = NOW();
            """, (user_name, consent))
            conn.commit()
    except Exception as e:
        raise Exception(f"Error updating user preferences: {e}")


def get_user_preferences(user_name: str):
    """
    Retrieve user preferences from the database.
    
    Args:
        user_name: The username from user_informations table
        
    Returns:
        tuple: (consent: bool, last_updated: datetime) or None
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT consent, last_updated FROM user_preferences WHERE user_name = %s;", (user_name,))
            return cur.fetchone()
    except Exception:
        return None


def update_user_collaboration(user_name: str, collaborative: bool):
    """
    Update the user's collaboration preference in the database.
    If the record doesn't exist, insert it.
    
    Args:
        user_name: The username from user_informations table
        collaborative: The collaboration preference value
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, collaborative, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET collaborative = EXCLUDED.collaborative, last_updated = NOW();
            """, (user_name, collaborative))
            conn.commit()
    except Exception as e:
        raise Exception(f"Error updating user collaboration: {e}")


def get_user_collaboration(user_name: str):
    """
    Retrieve the user's collaboration setting.
    
    Args:
        user_name: The username from user_informations table
        
    Returns:
        tuple: (collaborative: bool, last_updated: datetime) or None
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT collaborative, last_updated FROM user_preferences WHERE user_name = %s;", (user_name,))
            return cur.fetchone()
    except Exception:
        return None


def update_user_git_username(user_name: str, git_username: str):
    """
    Update or insert the user's GitHub username.
    
    Args:
        user_name: The username from user_informations table
        git_username: The GitHub username to store
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, git_username, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET git_username = EXCLUDED.git_username, last_updated = NOW();
            """, (user_name, git_username))
            conn.commit()
    except Exception as e:
        raise Exception(f"Error updating GitHub username: {e}")


def get_user_git_username(user_name: str):
    """
    Retrieve the user's GitHub username.
    
    Args:
        user_name: The username from user_informations table
        
    Returns:
        str or None
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT git_username FROM user_preferences WHERE user_name = %s;", (user_name,))
            result = cur.fetchone()
            return result[0] if result else None
    except Exception:
        return None
