"""Menu handlers for CLI interactions."""
import os
from project_display import select_project_interactive, list_projects_menu
from project_summarizer import summarize_project
from project_analyzer import analyze_project_by_id
from analysis.key_metrics import analyze_project_from_db
from analysis.project_ranking import rank_all_projects, display_rankings, rank_and_summarize_top_projects
from external_services.external_service_prompt import request_external_service_permission, ExternalServicePrompt
from external_services.permission_manager import ExternalServicePermission
from collaborative.identify_contributors import identify_contributors
from database.user_preferences import get_user_git_username, update_user_git_username
from tools.cleanup_insights import delete_insights


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


def ask_user_preferences(consent_manager, collab_manager, is_start):
    """Handle user preferences menu."""
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
            git_username = get_user_git_username()
            if not git_username:
                response = input("\nWhat is you GitHub user name: ").strip()
                update_user_git_username(response)
                just_changed = True
            print("\nYour github username is:"+str(get_user_git_username()))
            # Path to the ZIP file
            zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../test.zip"))
            ic = identify_contributors(zip_path=zip_path)
            # Extract the repo
            repo_path = ic.extract_repo()
            if repo_path is None:
                print("No git repository found in the ZIP.")
                return
            # Get the full contribution profile
            profile = ic.get_full_contribution_profile()
            ic.cleanup()
            
    if not just_changed and get_user_git_username() is not None and not is_start:
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


def handle_upload_file():
    """Handle file upload menu option."""
    filepath = input("Enter the path to your zip file: ")
    from upload_file import add_file_to_db
    add_file_to_db(filepath)


def handle_list_projects():
    """Handle list projects menu option."""
    list_projects_menu()


def handle_analyze_metrics():
    """Handle analyze project metrics menu option."""
    selected_project = select_project_interactive("Analyze project metrics")
    if selected_project:
        analyze_project_from_db(int(selected_project['id']))


def handle_rank_projects():
    """Handle rank all projects menu option."""
    print("\nRanking all projects...")
    ranked = rank_all_projects()
    display_rankings(ranked)
    input("\nPress Enter to continue...")


def handle_rank_and_summarize_projects():
    """Handle rank and summarize top 3 projects menu option."""
    rank_and_summarize_top_projects()
    input("\nPress Enter to continue...")


def handle_cleanup_insights():
    """Handle cleanup insights menu option."""
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

