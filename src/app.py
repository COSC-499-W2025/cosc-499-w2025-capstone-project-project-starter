"""Core application initialization and setup."""
from consent.consent_manager import ConsentManager
from collaborative.collaborative_manager import CollaborativeManager
from upload_file import init_uploaded_files_table
from database.user_informations import init_user_informations_table
from analysis.ranking_storage import init_ranking_storage_table
from resume.resume_manager import ResumeManager


def ensure_user_preferences_schema():
    """Ensure user_preferences table has git_username column."""
    try:
        from config.db_config import with_db_cursor
        with with_db_cursor() as cur:
            # Add git_username column if missing
            cur.execute("""
                ALTER TABLE user_preferences
                ADD COLUMN IF NOT EXISTS git_username VARCHAR(255);
            """)
    except Exception as e:
        print(f"[WARN] Exception caught: {e}")


def initialize_app():
    """
    Initialize the application: database, managers, and permissions.
    Returns tuple of (consent_manager, collab_manager) or None if initialization fails.
    """
    print("STARTING BACKEND SETUP...")
    
    # Initialize database tables
    # IMPORTANT: init_user_informations_table() must be called BEFORE init_uploaded_files_table()
    # because uploaded_files has a foreign key reference to user_informations.user_name
    try:
        init_user_informations_table()
        init_uploaded_files_table()
        init_ranking_storage_table()
        ResumeManager.init_resume_table()
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return None
    
    ensure_user_preferences_schema()
    
    # Initialize managers
    # ConsentManager will automatically get current logged-in user
    try:
        consent_manager = ConsentManager()
    except ValueError as e:
        print(f"Error initializing consent manager: {e}")
        return None
    
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
    try:
        from config.db_config import with_db_cursor
        with with_db_cursor() as _:
            print("Database is connected!")
    except Exception as e:
        print(f"Database is not connected: {e}")
        return None
    
    return consent_manager, collab_manager