"""Main CLI menu loop and routing."""
import os
import sys
from .menus import (
    handle_upload_file,
    handle_list_projects,
    handle_analyze_metrics_and_summary,
    analyze_project_menu,
    handle_rank_projects,
    handle_rank_and_summarize_projects,
    handle_view_edit_rankings,
    manage_external_services_menu,
    handle_cleanup_insights,
    ask_user_preferences,
    portfolio_menu,
    handle_generate_resume,
    handle_view_resume,
    handle_delete_resume
)
from cli.user_menus import user_account_menu
from account.user_manager import AuthManager


def run_main_menu(consent_manager, collab_manager):
    """Run the main menu loop."""
    while True:
        print("\n" + "="*70)
        print("MINING DIGITAL WORK ARTIFACTS - Main Menu")
        print("="*70)
        print("1. Upload a ZIP file")
        print("2. List stored projects")
        print("3. Analyze a project (FULL MODE: metrics + summary)")
        print("4. Analyze a project (PRIVACY MODE: analysis with local fallback)")
        print("5. Rank all projects")
        print("6. Rank and summarize top 3 projects")
        print("7. View and edit stored rankings")
        print("8. Manage external service settings")
        print("9. Cleanup insights for a project")
        print("10. Change User Preferences")
        # Display user account option with current user info
        if AuthManager.is_user_logged_in():
            current_user = AuthManager.get_current_username()
            print(f"11. User Account ({current_user})")
        else:
            print("11. User Account (Login/Register)")
        print("12. Generate Resume")
        print("13. View Resume")
        print("14. Delete Resume")
        print("15. View Portfolio")
        print("16. Exit")
        print("="*70) 
        
        if os.getenv("GITHUB_ACTIONS") == "true" or not sys.stdin.isatty():
            choice = "16"
        else:
            try:
                choice = input("Choose an option (1-16): ").strip()
            except EOFError:
                choice = "16"
        
        if choice == '1':
            handle_upload_file()
            
        elif choice == '2':
            handle_list_projects()
            
        elif choice == '3':
            handle_analyze_metrics_and_summary()
            
        elif choice == '4':
            analyze_project_menu()
            
        elif choice == '5':
            handle_rank_projects()
            
        elif choice == '6':
            handle_rank_and_summarize_projects()
            
        elif choice == '7':
            handle_view_edit_rankings()
            
        elif choice == '8':
            manage_external_services_menu()
            
        elif choice == '9':
            handle_cleanup_insights()
                
        elif choice == '10':
            ask_user_preferences(consent_manager, collab_manager, False)
            
        elif choice == '11':
            user_account_menu()
            
        elif choice == '12':
            handle_generate_resume()
            
        elif choice == '13':
            handle_view_resume()
            
        elif choice == '14':
            handle_delete_resume()
        
        elif choice == '15':
            portfolio_menu()
            
        elif choice == '16':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter 1-16.")
