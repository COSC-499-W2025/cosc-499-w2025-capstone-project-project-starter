from config.db_config import get_connection
from common.logger import setup_logger
logger = setup_logger(__name__)

def init_user_preferences_table():
    try:
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
                logger.info("Initialized user_preferences table.")
            else:
                logger.debug("user_preferences table already exists.")
    except Exception as e:
        logger.error(f"Error initializing user_preferences table: {e}")
        raise

def update_user_preferences(user_name: str, consent: bool):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, consent, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET consent = EXCLUDED.consent, last_updated = NOW();
            """, (user_name, consent))
            conn.commit()
            logger.info(f"Updated user preferences for {user_name}: consent={consent}")
    except Exception as e:
        logger.error(f"Error updating user preferences for {user_name}: {e}")
        raise Exception(f"Error updating user preferences: {e}")

def get_user_preferences(user_name: str):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT consent, last_updated FROM user_preferences WHERE user_name = %s;", (user_name,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Error retrieving user preferences for {user_name}: {e}")
        return None


def update_user_collaboration(user_name: str, collaborative: bool):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, collaborative, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET collaborative = EXCLUDED.collaborative, last_updated = NOW();
            """, (user_name, collaborative))
            conn.commit()
            logger.info(f"Updated collaboration preference for {user_name}: collaborative={collaborative}")
    except Exception as e:
        logger.error(f"Error updating user collaboration for {user_name}: {e}")
        raise Exception(f"Error updating user collaboration: {e}")


def get_user_collaboration(user_name: str):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT collaborative, last_updated FROM user_preferences WHERE user_name = %s;", (user_name,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Error retrieving user collaboration for {user_name}: {e}")
        return None


def update_user_git_username(user_name: str, git_username: str):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (user_name, git_username, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_name)
                DO UPDATE SET git_username = EXCLUDED.git_username, last_updated = NOW();
            """, (user_name, git_username))
            conn.commit()
            logger.info(f"Updated git username for {user_name}")
    except Exception as e:
        logger.error(f"Error updating GitHub username for {user_name}: {e}")
        raise Exception(f"Error updating GitHub username: {e}")


def get_user_git_username(user_name: str):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT git_username FROM user_preferences WHERE user_name = %s;", (user_name,))
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error retrieving git username for {user_name}: {e}")
        return None