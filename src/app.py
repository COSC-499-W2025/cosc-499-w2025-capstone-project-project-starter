"""Core application initialization and setup."""
from config.db_config import get_connection
from consent.consent_manager import ConsentManager
from collaborative.collaborative_manager import CollaborativeManager
from upload_file import init_uploaded_files_table
from analysis.ranking_storage import init_ranking_storage_table


def ensure_user_preferences_schema():
    """Debug version to check why git_username is not being added."""
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
            table_exists = cur.fetchone()[0]
            print("Table exists:", table_exists)
            
            # Add git_username column if missing
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = 'user_preferences' AND column_name = 'git_username';
            """)
            column_exists = cur.fetchone()
            print("git_username column exists before ALTER:", column_exists)
            cur.execute("""
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS git_username VARCHAR(255);
            """)
            # Check after
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = 'user_preferences' AND column_name = 'git_username';
            """)
            column_exists_after = cur.fetchone()
            print("git_username column exists after ALTER:", column_exists_after)
            conn.commit()
    except Exception as e:
        print(f"[WARN] Exception caught: {e}")


def initialize_app():
    """
    Initialize the application: database, managers, and permissions.
    Returns tuple of (consent_manager, collab_manager) or None if initialization fails.
    """
    print("STARTING BACKEND SETUP...")
    
    # Initialize database tables
    try:
        init_uploaded_files_table()
        init_ranking_storage_table()
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return None
    
    ensure_user_preferences_schema()
    
    # Initialize managers
    consent_manager = ConsentManager(user_id="default_user")
    collab_manager = CollaborativeManager()
    
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

