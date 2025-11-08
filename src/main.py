"""Main entry point for the application."""
from app import initialize_app
from cli.main_menu import run_main_menu


def main():
    """Main entry point - initializes app and runs CLI."""
    managers = initialize_app()
    if managers is None:
        return
    
    consent_manager, collab_manager = managers
    run_main_menu(consent_manager, collab_manager)

if __name__ == "__main__":
    main()