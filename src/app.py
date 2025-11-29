"""Core application initialization and setup."""
from config.db_config import get_connection
from consent.consent_manager import ConsentManager
from collaborative.collaborative_manager import CollaborativeManager
from upload_file import init_uploaded_files_table
from database.user_informations import init_user_informations_table
from analysis.ranking_storage import init_ranking_storage_table


def ensure_user_preferences_schema():
    """
    Ensure user_preferences table has required schema including git_username column.
    This function handles schema migrations for the user_preferences table.
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            # Check if table exists first
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'user_preferences'
                );
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                # Table doesn't exist - this is a real problem, not just a missing column
                raise Exception("user_preferences table does not exist. Table must be initialized first.")
            
            # Table exists, safely add column if missing (idempotent operation)
            cur.execute("""
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS git_username VARCHAR(255);
            """)
            conn.commit()
    except Exception as e:
        # Re-raise exception to surface real migration problems
        print(f"[ERROR] Failed to update user_preferences schema: {e}")
        raise


def initialize_app():
    """
    Initialize the application: database, managers, and permissions.
    Returns tuple of (consent_manager, collab_manager) or None if initialization fails.
    """
    print("STARTING BACKEND SETUP...")
    
    # Initialize database tables
    try:
        init_uploaded_files_table()
        init_user_informations_table()
        init_ranking_storage_table()
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return None
    
    # Initialize managers (this also initializes user_preferences table)
    consent_manager = ConsentManager(user_id="default_user")
    collab_manager = CollaborativeManager()
    
    # Now ensure schema is up to date (table should exist after manager initialization)
    ensure_user_preferences_schema()
    
    consent_manager.initialize()
    
    # Check/request user consent
    if not consent_manager.request_consent_if_needed():
        print("Consent not granted. Exiting...")
        return None
    else:
        print("User consent granted. Proceeding with backend setup.")
    
    # Check/request collaborative consent
    if not collab_manager.request_collaborative_if_needed():
        print("Collaborative not granted. Doing individual.")
    else:
        print("Collaborative granted. Doing collaborative and individual.")

    # Test database connection
    conn = get_connection()
    if conn:
        print("Database is connected!")
        conn.close()
    else:
        print("Database is not connected.")
        return None
    
    return consent_manager, collab_manager

