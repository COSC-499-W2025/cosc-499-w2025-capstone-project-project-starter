from config.db_config import get_connection
from upload_file import add_file_to_db
from project_display import select_project_interactive, list_projects_menu
from consent.consent_manager import ConsentManager
from collaborative.collaborative_manager import CollaborativeManager
from analysis.key_metrics import analyze_project_from_db
from analysis.project_ranking import rank_all_projects, display_rankings
from project_summarizer import summarize_project
from external_services.external_service_prompt import request_external_service_permission
from project_analyzer import analyze_project_by_id
import os
import sys
from collaborative.identify_contributors import identify_contributors
from database.user_preferences import get_user_git_username, update_user_git_username
from tools.cleanup_insights import delete_insights

consent_manager = ConsentManager(user_id="default_user")
collab_manager = CollaborativeManager()

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

def display_success(result):
    """Display success information to user."""
    print("\n" + "="*70)
    print("SUCCESS")
    print("="*70)
    
    if hasattr(result, 'message') and result.message:
        print(f"Message: {result.message}")
    
    if hasattr(result, 'data') and result.data:
        data = result.data
        
        # Display file information
        if 'filename' in data:
            print(f"File: {data['filename']}")
        
        if 'file_id' in data:
            print(f"File ID: {data['file_id']}")
        
        # Display file list
        if 'files' in data and data['files']:
            files = data['files']
            file_count = len(files)
            
            print(f"\n{file_count} files:")
            
            # Show first 5 files
            for i, file in enumerate(files[:5], 1):
                print(f"  {i}. {file}")
            
            # If more than 5 files, indicate there are more
            if file_count > 5:
                print(f"  ... and {file_count - 5} more files")
        
        # Display file count if provided
        if 'file_count' in data and 'files' not in data:
            print(f"Total files: {data['file_count']}")
    
    print("="*70 + "\n")


def summarize_project_menu():
    """Handle the project summarization menu."""
    print("\n" + "-"*50)
    print("Project Summarization")
    print("-"*50)
    
    selected_project = select_project_interactive("Project Summarization")
    if not selected_project:
        return
    print(f"\nGenerating summary for: {selected_project['filename']}")
    print("Please wait...")
    summary = summarize_project(selected_project['id'])
    print(summary)
    input("\nPress Enter to continue...")

def display_error(result):
    """Format and display error information"""
    print("\n" + "="*60)
    print("ERROR")
    print("="*60)
    print(f"Error Type: {result.error_type}")
    print(f"Message: {result.message}")
    if result.data:
        print("\nDetails:")
        for key, value in result.data.items():
            print(f"  • {key}: {value}")
    print("="*60 + "\n")

def ask_user_preferences(is_start):
    just_changed = False
    
    # Check/request user consent first
    if not is_start and consent_manager.has_access():
        # Allow user to withdraw consent
        response = input("\nWould you like to withdraw consent? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            consent_manager.withdraw()
    # Request consent if needed (for is_start=True or if consent was withdrawn)
    else:
        consent_manager.request_consent_if_needed()
    
    prefs = collab_manager.get_preferences()
    if prefs and prefs[1] and not is_start: 
        while True:
            response = input("\nWould you like to not include collaborative work? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                collab_manager.update_collaborative(False)
                print("\nCollaborative not granted. Thank you!")
                break
            elif response in ['no', 'n']:
                break
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")
    else:
        # Check/request collaborative consent
        if not collab_manager.request_collaborative_if_needed():
            print("Collaborative not granted. Doing individual.")
        else:
            print("Collaborative granted. Doing colabrative and individual.")
            if not get_user_git_username() or get_user_git_username()[0] is None:
                response = input("\nWhat is you GitHub user name: ").strip()
                update_user_git_username(response)
                just_changed = True
            print("\nYour github username is:"+str(get_user_git_username()))
            # Path to the ZIP file
            zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../test.zip"))
            ic = identify_contributors(zip_path=zip_path)
            # Extract the repo
            repo_path = ic.extract_repo()
            if repo_path is None:
                print("No git repository found in the ZIP.")
                return
            # Get the full contribution profile
            profile = ic.get_full_contribution_profile()
            ic.cleanup()
                
        if not just_changed and not get_user_git_username()[0] is None and not is_start:
            while True:
                response = input("\nWould you like to change you GitHub username? (y/n) ")
                if response in ['yes', 'y']:
                    new_username = input("\nWhat is you GitHub user name: ").strip()
                    update_user_git_username(new_username)
                    break
                elif response in ['no', 'n']:
                    break
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")

def analyze_project_menu():
    """
    Handle the project analysis menu.
    This is the main menu for Issue #10: Analysis if User Declines Outside Sources.
    """
    selected_project = select_project_interactive("Project Analysis (with Local Fallback)")
    
    if not selected_project:
        return
    
    print(f"\nAnalyzing: {selected_project['filename']}")
    print("Please wait...")
    
    # Perform analysis (respects user's external service permission)
    analyze_project_by_id(selected_project['id'])
    
    # Ask if user wants to continue
    continue_choice = input("\nPress Enter to continue or 'q' to quit: ").strip()
    if continue_choice.lower() == 'q':
        return

def manage_external_services_menu():
    """
    Manage external service permissions (settings menu).
    Issue #10: Allow user to manage external service preferences.
    """
    print("\n" + "-"*50)
    print("External Service Settings")
    print("-"*50)
    print("1. View current permission status")
    print("2. Grant/Update external service permission")
    print("3. Revoke external service permission")
    print("4. Back to main menu")
    print("-"*50)
    
    choice = input("Choose an option (1-4): ").strip()
    
    if choice == '1':
        # View current status
        from external_services.permission_manager import ExternalServicePermission
        permission_manager = ExternalServicePermission('default_user')
        has_permission = permission_manager.has_permission('LLM')
        
        print("\n" + "="*50)
        if has_permission is None:
            print("Status: No permission set (will be asked on first analysis)")
        elif has_permission:
            print("Status: External service permission GRANTED")
            print("  Enhanced analysis is enabled")
        else:
            print("Status: External service permission DECLINED")
            print("  Local analysis only (data stays private)")
        print("="*50)
        
    elif choice == '2':
        # Grant/Update permission
        request_external_service_permission('default_user', 'LLM')
        
    elif choice == '3':
        # Revoke permission
        from external_services.external_service_prompt import ExternalServicePrompt
        confirm = input("\nAre you sure you want to revoke external service permission? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            ExternalServicePrompt.store_permission('default_user', 'LLM', False)
            print("\nExternal service permission has been REVOKED")
            print("  Local analysis will be used (your data stays private)")
        else:
            print("\nAction cancelled")
    
    elif choice == '4':
        return
    else:
        print("Invalid choice. Please enter 1, 2, 3, or 4.")

def main():
    print("STARTING BACKEND SETUP...")
    
    # Initialize database tables
    try:
        from upload_file import init_uploaded_files_table
        init_uploaded_files_table()
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return
    
    ensure_user_preferences_schema()
    consent_manager.initialize()
    
    # Check/request user consent
    if not consent_manager.request_consent_if_needed():
        print("Consent not granted. Exiting...")
        return
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
        return
    
    # Main menu interface
    while True:
        print("\n" + "="*70)
        print("MINING DIGITAL WORK ARTIFACTS - Main Menu")
        print("="*70)
        print("1. Upload a ZIP file")
        print("2. List stored projects")
        print("3. Analyze project metrics")
        print("4. Summarize a project (basic summary)")
        print("5. Analyze a project (detailed analysis with local fallback)")
        print("6. Rank all projects")
        print("7. Manage external service settings")
        print("8. Cleanup insights for a project")
        print("9. Change User Preferences")
        print("10. Exit")
        print("="*70) 
        
        if os.getenv("GITHUB_ACTIONS") == "true" or not sys.stdin.isatty():
            choice = "10"
        else:
            try:
                choice = input("Choose an option (1-10): ").strip()
            except EOFError:
                choice = "10"
        
        if choice == '1':
            filepath = input("Enter the path to your zip file: ")
            add_file_to_db(filepath)
            
        elif choice == '2':
            list_projects_menu()
            
        elif choice == '3':
            selected_project = select_project_interactive("Analyze project metrics")
            if selected_project:
                analyze_project_from_db(int(selected_project['id']))
                
        elif choice == '4':
            summarize_project_menu()
            
        elif choice == '5':
            analyze_project_menu()
            
        elif choice == '6':
            print("\nRanking all projects...")
            ranked = rank_all_projects()
            display_rankings(ranked)
            input("\nPress Enter to continue...")
            
        elif choice == '7':
            manage_external_services_menu()
            
        elif choice == '8':
            pid = input("Enter project ID to clean: ").strip()
            if pid.isdigit():
                confirm = input(
                    f"Delete insights and the uploaded file for project {pid}? "
                    f"This cannot be undone. (y/n): "
                ).strip().lower()
                if confirm in ('y', 'yes'):
                    m, f, p = delete_insights(int(pid))
                    print(f"Deleted: project_metrics={m}, file_contents={f}, uploaded_files={p}")
                else:
                    print("Cancelled.")
            else:
                print("Invalid project ID.")
                
        elif choice == '9':
            ask_user_preferences(False)

        elif choice == '10':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter 1-10.")

if __name__ == "__main__":
    main()