"""Main entry point for the application."""
from app import initialize_database, initialize_managers
from cli.main_menu import run_main_menu
from cli.user_menus import login_menu
from account.user_manager import AuthManager


def main():
    """Main entry point - initializes app and runs CLI."""
    # Step 1: Initialize database tables (before login)
    if not initialize_database():
        print("Failed to initialize database. Exiting...")
        return
    
    # Step 2: User login
    # Check if user is already logged in from a previous session
    if not AuthManager.is_user_logged_in():
        # Show login menu if no user is logged in
        if not login_menu():
            # User chose to exit from login menu
            return
    
    # Step 3: Initialize managers (after login)
    managers = initialize_managers()
    if managers is None:
        print("Failed to initialize managers. Exiting...")
        return
    
    consent_manager, collab_manager = managers
    
    # User is now logged in, show main menu
    run_main_menu(consent_manager, collab_manager)

if __name__ == "__main__":
    main()