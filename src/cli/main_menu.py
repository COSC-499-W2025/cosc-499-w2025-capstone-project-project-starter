"""Main CLI menu loop and routing."""
import os
import sys
from .menus import (
    project_menu,
    analysis_menu,
    handle_rank_projects,
    handle_rank_and_summarize_projects,
    handle_view_edit_rankings,
    settings_menu,
    resume_menu,
    portfolio_menu,
    handle_llm_summary,
    handle_zip_success_report
)
from account.user_manager import AuthManager

MENU_ITEMS = [
    "List/Manage projects",                               # 1
    "Analyze a project",                                  # 2
    "Rank all projects",                                  # 3
    "Rank and summarize top 3 projects",                  # 4
    "View and edit stored rankings",                      # 5
    "Settings",                                           # 6
    "Resume",                                             # 7
    "Portfolio",                                          # 8
    "Run LLM summary (test.zip)",                         # 9
    "Project success report (ZIP)",                       # 10
    "Exit"                                                # 11
]

def run_main_menu(consent_manager, collab_manager):
    """Run the main menu loop."""
    while True:
        # Check if user is still logged in (in case of session timeout or logout)
        if not AuthManager.is_user_logged_in():
            print("\nSession expired or user logged out. Please log in again.")
            from cli.user_menus import login_menu
            if not login_menu():
                # User chose to exit
                return
        
        print("\n" + "="*70)
        print("MINING DIGITAL WORK ARTIFACTS - Main Menu")
        print("="*70)
        
        # Show user info
        current_user = AuthManager.get_current_username()
        print(f"Logged in as: {current_user}")
        print("="*70)
        
        for idx, label in enumerate(MENU_ITEMS, start=1):
            print(f"{idx}. {label}")

        print("="*70) 
        
        if os.getenv("GITHUB_ACTIONS") == "true" or not sys.stdin.isatty():
            choice = "11"
        else:
            try:
                choice = input("Choose an option (1-11): ").strip()
            except EOFError:
                choice = "11"
        
        # Check authentication before processing any choice
        if not AuthManager.is_user_logged_in():
            print("Error: User session invalid. Please log in again.")
            continue
            
        handlers = {
            "1": lambda: project_menu(),
            "2": lambda: analysis_menu(),
            "3": lambda: handle_rank_projects(),
            "4": lambda: handle_rank_and_summarize_projects(),
            "5": lambda: handle_view_edit_rankings(),
            "6": lambda: settings_menu(consent_manager, collab_manager),
            "7": lambda: resume_menu(),
            "8": lambda: portfolio_menu(),
            "9": lambda: handle_llm_summary(),
            "10": lambda: handle_zip_success_report(),
            "11": "EXIT"
        }

        handler = handlers.get(choice)

        if handler is None:
            print("Invalid choice. Please enter 1-11.")
            continue

        if handler == "EXIT":
            if AuthManager.is_user_logged_in():
                current_user = AuthManager.get_current_username()
                AuthManager.logout()
                print(f"Logging out {current_user}...")
            print("Goodbye!")
            break

        handler()
