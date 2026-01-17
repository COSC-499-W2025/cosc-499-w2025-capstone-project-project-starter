"""
Project display and selection UI functions.
Handles all user interface interactions for listing and selecting projects.
"""
from project_manager import list_projects, list_project_files
from project_summarizer import get_available_projects
from account.user_manager import AuthManager


def select_project_interactive(title: str):
    """
    Unified project selection UI. Returns selected project dict or None.
    
    Args:
        title: Title to display for the selection menu
        
    Returns:
        Selected project dictionary or None if cancelled
    """
    print("\n" + "-"*50)
    print(title)
    print("-"*50)

    projects = get_available_projects()

    if not projects:
        print("No projects found in database.")
        print("Please upload a project first using option 1.")
        return None

    print("Available projects:")
    for i, project in enumerate(projects, 1):
        created_date = project['created_at'].strftime("%Y-%m-%d") if project['created_at'] else "Unknown"
        print(f"{i}. {project['filename']} (ID: {project['id']}, Created: {created_date})")

    print("-"*50)

    while True:
        try:
            choice = input(f"Select a project (1-{len(projects)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(projects):
                return projects[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(projects)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")


def list_projects_menu():
    """
    Handle the list projects menu option.
    Lists all stored projects and allows viewing files within a selected project.
    Data Isolation: Uses current user's username to filter projects.
    """
    # Get current logged-in user for data isolation
    current_username = AuthManager.get_current_username()
    if not current_username:
        print("Error: No user is currently logged in.")
        return
    
    # Data Isolation: Pass user_name to list only current user's projects
    projects = list_projects(current_username)
    if projects:
        print("\nWould you like to view files for a specific project?")
        view_choice = input("Enter project number to view files, or 'q' to go back: ").strip()
        if view_choice.lower() != 'q':
            try:
                project_num = int(view_choice)
                if 1 <= project_num <= len(projects):
                    selected_project = projects[project_num - 1]
                    print(f"\n" + "-"*80)
                    print(f"Files in project: {selected_project['filename']}")
                    print("-"*80)
                    # Data Isolation: Pass user_name to verify project ownership
                    files = list_project_files(selected_project['id'], current_username)
                    if files:
                        for i, file_path in enumerate(files, 1):
                            print(f"{i}. {file_path}")
                        print("-"*80)
                        print(f"Total files: {len(files)}")
                    input("\nPress Enter to continue...")
                else:
                    print(f"Please enter a number between 1 and {len(projects)}")
            except ValueError:
                print("Please enter a valid number or 'q'")

