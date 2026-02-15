"""
Portfolio Display Module

Handles displaying portfolio information in the CLI.
"""

from portfolio.portfolio_manager import PortfolioManager
from portfolio.portfolio_formatter import PortfolioFormatter
from account.user_manager import AuthManager


def display_portfolio(user_name: str = None, format_type: str = 'text', top_n: int = None):
    """
    Display analytical portfolio report.
    
    Args:
        user_name: Username (string) to filter projects.
                  If None, uses the currently logged-in user.
        format_type: Output format ('text', 'markdown')
        top_n: If specified, only show top N projects
    """
    # Get current logged-in user if user_name not provided
    if user_name is None:
        if not AuthManager.is_user_logged_in():
            print("\nError: You must be logged in to view portfolio.")
            return
        current_user = AuthManager.get_current_user()
        user_name = current_user.get('user_name', 'default_user') if current_user else 'default_user'
    
    print("\n" + "="*80)
    print("GENERATING PORTFOLIO REPORT...")
    print("="*80)
    print("Please wait, this may take a moment...\n")
    
    manager = PortfolioManager(user_name)
    
    # Generate portfolio report using existing functions
    portfolio_data = manager.generate_portfolio_report(top_n=top_n)
    
    if 'error' in portfolio_data:
        print(f"\nError generating portfolio: {portfolio_data['error']}")
        return
    
    # Format and display
    formatter = PortfolioFormatter()
    formatted = formatter.get_formatted_portfolio(portfolio_data, format_type)
    
    if formatted:
        print(formatted)
    else:
        print("Error formatting portfolio.")


def portfolio_menu():
    """Interactive menu for portfolio options."""
    
    # Get current logged-in user
    if not AuthManager.is_user_logged_in():
        print("\nError: You must be logged in to view portfolio.")
        input("\nPress Enter to continue...")
        return
    
    current_user = AuthManager.get_current_user()
    user_name = current_user.get('user_name', 'default_user') if current_user else 'default_user'
    
    print("\n" + "="*80)
    print("PORTFOLIO MENU")
    print("="*80)
    print("1. View full portfolio report (all projects)")
    print("2. View portfolio report (top 5 projects)")
    print("3. View portfolio report (top 10 projects)")
    print("4. Export portfolio as Markdown")
    print("5. Customize portfolio project information")
    print("6. Back to main menu")
    print("="*80)
    
    choice = input("Choose an option (1-6): ").strip()
    
    if choice == '1':
        display_portfolio(user_name=user_name)
        input("\nPress Enter to continue...")
    
    elif choice == '2':
        display_portfolio(user_name=user_name, top_n=5)
        input("\nPress Enter to continue...")
    
    elif choice == '3':
        display_portfolio(user_name=user_name, top_n=10)
        input("\nPress Enter to continue...")
    
    elif choice == '4':
        print("\nGenerating Markdown portfolio report...")
        manager = PortfolioManager(user_name=user_name)
        portfolio_data = manager.generate_portfolio_report()
        
        if 'error' not in portfolio_data:
            formatter = PortfolioFormatter()
            markdown_output = formatter.format_markdown(portfolio_data)
            
            if markdown_output:
                # Option to save to file
                save = input("\nSave to file? (y/n): ").strip().lower()
                if save in ['y', 'yes']:
                    filename = input("Enter filename (default: portfolio_report.md): ").strip()
                    if not filename:
                        filename = "portfolio_report.md"
                    if not filename.endswith('.md'):
                        filename += '.md'
                    
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(markdown_output)
                        print(f"\nPortfolio report saved to {filename}")
                    except Exception as e:
                        print(f"\nError saving file: {e}")
                else:
                    print("\n" + markdown_output)
        else:
            print(f"\nError: {portfolio_data.get('error', 'Unknown error')}")
        
        input("\nPress Enter to continue...")
    
    elif choice == '5':
        customize_portfolio_project(user_name)
        input("\nPress Enter to continue...")
    
    elif choice == '6':
        return
    
    else:
        print("Invalid choice. Please enter 1-6.")


def customize_portfolio_project(user_name: str):
    """Interactive menu to customize portfolio project information."""
    from project_manager import list_projects, get_project_by_id
    from resume.resume_manager import ResumeManager
    
    while True:
        print("\n" + "="*80)
        print("CUSTOMIZE PORTFOLIO PROJECT")
        print("="*80)
        
        # List user's projects
        projects = list_projects(user_name=user_name)
        
        if not projects:
            print("\nYou don't have any projects yet. Upload projects first.")
            return
        
        print("\nMenu Options:")
        print("1. Customize a project")
        print("2. List existing customizations")
        print("3. Clear a project customization")
        print("4. Back to portfolio menu")
        print("="*80)
        
        choice = input("\nChoose an option (1-4): ").strip()
        
        if choice == '1':
            # Display projects with numbering
            print("\n" + "-" * 80)
            print("Your Projects:")
            print("-" * 80)
            for idx, project in enumerate(projects, 1):
                project_id = project.get('id')
                filename = project.get('filename', 'Unknown')
                
                # Check if this project has customization
                customization = ResumeManager.get_portfolio_customization(user_name, project_id)
                marker = " [CUSTOMIZED]" if customization else ""
                
                print(f"{idx}. {filename} (ID: {project_id}){marker}")
            
            print("-" * 80)
            project_choice = input(f"\nEnter project number (1-{len(projects)}) or 'back' to cancel: ").strip().lower()
            
            if project_choice == 'back':
                continue
            
            try:
                project_idx = int(project_choice)
                if 1 <= project_idx <= len(projects):
                    selected_project = projects[project_idx - 1]
                    _customize_single_project(user_name, selected_project)
                else:
                    print(f"\nInvalid project number. Please enter 1-{len(projects)}.")
            except ValueError:
                print("\nInvalid input. Please enter a valid number.")
        
        elif choice == '2':
            _list_portfolio_customizations(user_name)
        
        elif choice == '3':
            _clear_portfolio_customization(user_name, projects)
        
        elif choice == '4':
            return
        
        else:
            print("\nInvalid choice. Please enter 1-4.")


def _customize_single_project(user_name: str, project: dict):
    """Customize a single portfolio project."""
    from resume.resume_manager import ResumeManager
    
    project_id = project.get('id')
    filename = project.get('filename', 'Unknown')
    
    print("\n" + "="*80)
    print(f"CUSTOMIZING: {filename}")
    print("="*80)
    
    # Load existing customization if any
    existing = ResumeManager.get_portfolio_customization(user_name, project_id)
    
    if existing:
        print("\nExisting Customization:")
        print(f"  Title: {existing.get('custom_title') or '(not set)'}")
        print(f"  Description: {existing.get('custom_description') or '(not set)'}")
        print(f"  Role: {existing.get('custom_role') or '(not set)'}")
        print()
    
    print("Enter custom information for this project.")
    print("(Press Enter to keep existing value or leave blank)")
    print("-" * 80)
    
    # Get custom title
    current_title = existing.get('custom_title', '') if existing else ''
    prompt_title = f"Custom Title [{current_title}]: " if current_title else "Custom Title: "
    custom_title = input(prompt_title).strip()
    if not custom_title and current_title:
        custom_title = current_title
    
    # Get custom description
    current_desc = existing.get('custom_description', '') if existing else ''
    prompt_desc = f"Custom Description [{current_desc[:50]}...]: " if current_desc else "Custom Description: "
    custom_description = input(prompt_desc).strip()
    if not custom_description and current_desc:
        custom_description = current_desc
    
    # Get custom role
    current_role = existing.get('custom_role', '') if existing else ''
    prompt_role = f"Custom Role [{current_role}]: " if current_role else "Custom Role: "
    custom_role = input(prompt_role).strip()
    if not custom_role and current_role:
        custom_role = current_role
    
    # Confirm before saving
    print("\n" + "-" * 80)
    print("Summary of changes:")
    print(f"  Title: {custom_title or '(not set)'}")
    print(f"  Description: {custom_description or '(not set)'}")
    print(f"  Role: {custom_role or '(not set)'}")
    print("-" * 80)
    
    confirm = input("\nSave these customizations? (y/n): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        custom_data = {
            'custom_title': custom_title,
            'custom_description': custom_description,
            'custom_role': custom_role
        }
        
        success = ResumeManager.save_portfolio_customization(user_name, project_id, custom_data)
        
        if success:
            print("\n✓ Portfolio customization saved successfully!")
            print("  Your custom information will be used when generating portfolio reports.")
        else:
            print("\n✗ Failed to save customization. Please try again.")
    else:
        print("\nCancelled. No changes were saved.")


def _list_portfolio_customizations(user_name: str):
    """List all portfolio customizations for the user."""
    from resume.resume_manager import ResumeManager
    from project_manager import get_project_by_id
    
    print("\n" + "="*80)
    print("YOUR PORTFOLIO CUSTOMIZATIONS")
    print("="*80)
    
    customized_ids = ResumeManager.list_customized_portfolio_projects(user_name)
    
    if not customized_ids:
        print("\nYou haven't customized any portfolio projects yet.")
        return
    
    print(f"\nYou have customized {len(customized_ids)} project(s):\n")
    
    for project_id in customized_ids:
        try:
            project = get_project_by_id(project_id, user_name=user_name)
            customization = ResumeManager.get_portfolio_customization(user_name, project_id)
            
            if project and customization:
                print(f"Project: {project.get('filename', 'Unknown')} (ID: {project_id})")
                print(f"  Custom Title: {customization.get('custom_title') or '(not set)'}")
                print(f"  Custom Description: {customization.get('custom_description', '')[:80] or '(not set)'}...")
                print(f"  Custom Role: {customization.get('custom_role') or '(not set)'}")
                print("-" * 80)
        except Exception as e:
            print(f"\nWarning: Could not load project {project_id}: {e}")
            continue


def _clear_portfolio_customization(user_name: str, projects: list):
    """Clear portfolio customization for a project."""
    from resume.resume_manager import ResumeManager
    
    print("\n" + "="*80)
    print("CLEAR PORTFOLIO CUSTOMIZATION")
    print("="*80)
    
    # Show only customized projects
    customized_ids = ResumeManager.list_customized_portfolio_projects(user_name)
    
    if not customized_ids:
        print("\nYou haven't customized any portfolio projects yet.")
        return
    
    # Filter to show only customized projects
    customized_projects = [p for p in projects if p.get('id') in customized_ids]
    
    print("\nCustomized Projects:")
    print("-" * 80)
    for idx, project in enumerate(customized_projects, 1):
        project_id = project.get('id')
        filename = project.get('filename', 'Unknown')
        print(f"{idx}. {filename} (ID: {project_id})")
    
    print("-" * 80)
    choice = input(f"\nEnter project number to clear (1-{len(customized_projects)}) or 'back' to cancel: ").strip().lower()
    
    if choice == 'back':
        return
    
    try:
        project_idx = int(choice)
        if 1 <= project_idx <= len(customized_projects):
            selected_project = customized_projects[project_idx - 1]
            project_id = selected_project.get('id')
            filename = selected_project.get('filename', 'Unknown')
            
            confirm = input(f"\nAre you sure you want to clear customization for '{filename}'? (y/n): ").strip().lower()
            
            if confirm in ['y', 'yes']:
                success = ResumeManager.clear_portfolio_customization(user_name, project_id)
                
                if success:
                    print("\n✓ Portfolio customization cleared successfully!")
                    print("  The project will use auto-generated information in portfolio reports.")
                else:
                    print("\n✗ Failed to clear customization. Please try again.")
            else:
                print("\nCancelled.")
        else:
            print(f"\nInvalid project number. Please enter 1-{len(customized_projects)}.")
    except ValueError:
        print("\nInvalid input. Please enter a number or 'back'.")
