"""Main entry point for the application."""
from app import initialize_app
from cli.main_menu import run_main_menu
from cli.user_menus import login_menu
from account.user_manager import AuthManager


def main():
    """Main entry point - initializes app and runs CLI."""
    managers = initialize_app()
    if managers is None:
        return
    
    consent_manager, collab_manager = managers
    
    # Check if user is already logged in from a previous session
    if not AuthManager.is_user_logged_in():
        # Show login menu if no user is logged in
        if not login_menu():
            # User chose to exit from login menu
            return
    
    # User is now logged in, show main menu
    run_main_menu(consent_manager, collab_manager)

if __name__ == "__main__":
    main()