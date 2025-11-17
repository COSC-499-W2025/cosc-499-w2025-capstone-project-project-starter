"""User account menu handlers for CLI interactions."""
import os
import getpass
from account.user_manager import AuthManager


def user_account_menu():
    """Handle user account management menu."""
    while True:
        print("\n" + "="*50)
        print("USER ACCOUNT MANAGEMENT")
        print("="*50)
        
        if AuthManager.is_user_logged_in():
            # User is logged in - show user info and logout option
            current_user = AuthManager.get_current_username()
            user_info = AuthManager.get_current_user()
            
            print(f"Currently logged in as: {current_user}")
            if user_info:
                print(f"User ID: {user_info['user_id']}")
                if user_info.get('create_time'):
                    print(f"Account created: {user_info['create_time']}")
                if user_info.get('last_login_time'):
                    print(f"Last login: {user_info['last_login_time']}")
            
            print("\nOptions:")
            print("1. Logout")
            print("2. Back to main menu")
            print("="*50)
            
            choice = input("Choose an option (1-2): ").strip()
            
            if choice == '1':
                handle_user_logout()
            elif choice == '2':
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
        else:
            # User is not logged in - show login and register options
            print("You are not currently logged in.")
            print("\nOptions:")
            print("1. Login to existing account")
            print("2. Create new account")
            print("3. Back to main menu")
            print("="*50)
            
            choice = input("Choose an option (1-3): ").strip()
            
            if choice == '1':
                handle_user_login()
            elif choice == '2':
                handle_user_registration()
            elif choice == '3':
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")


def handle_user_login():
    """Handle user login process."""
    print("\n" + "-"*40)
    print("USER LOGIN")
    print("-"*40)
    
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return
    
    try:
        password = getpass.getpass("Password: ")
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
        return
    except Exception:
        # Fallback to regular input if getpass fails
        password = input("Password: ").strip()
    
    if not password:
        print("Password cannot be empty.")
        return
    
    result = AuthManager.login(username, password)
    
    if result['success']:
        print(f"\n✓ {result['message']}")
        print(f"Welcome back, {username}!")
        input("\nPress Enter to continue...")
    else:
        print(f"\n✗ {result['message']}")
        input("\nPress Enter to continue...")


def handle_user_logout():
    """Handle user logout process."""
    current_user = AuthManager.get_current_username()
    
    confirm = input(f"Are you sure you want to logout from '{current_user}'? (y/n): ").strip().lower()
    
    if confirm in ('y', 'yes'):
        result = AuthManager.logout()
        
        if result['success']:
            print(f"\n✓ {result['message']}")
            print("You have been logged out.")
        else:
            print(f"\n✗ {result['message']}")
        
        input("\nPress Enter to continue...")


def handle_user_registration():
    """Handle user registration process."""
    print("\n" + "-"*40)
    print("CREATE NEW ACCOUNT")
    print("-"*40)
    
    username = input("Choose a username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return
    
    try:
        password = getpass.getpass("Choose a password (minimum 6 characters): ")
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return
    except Exception:
        # Fallback to regular input if getpass fails
        password = input("Choose a password (minimum 6 characters): ").strip()
    
    if not password:
        print("Password cannot be empty.")
        return
    
    try:
        confirm_password = getpass.getpass("Confirm password: ")
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return
    except Exception:
        # Fallback to regular input if getpass fails
        confirm_password = input("Confirm password: ").strip()
    
    if password != confirm_password:
        print("Passwords do not match.")
        return
    
    result = AuthManager.register(username, password)
    
    if result['success']:
        print(f"\n✓ {result['message']}")
        print(f"Account created successfully! User ID: {result['user_id']}")
        
        # Ask if user wants to login immediately
        login_now = input("\nWould you like to login now? (y/n): ").strip().lower()
        if login_now in ('y', 'yes'):
            login_result = AuthManager.login(username, password)
            if login_result['success']:
                print(f"\n✓ {login_result['message']}")
                print(f"Welcome, {username}!")
    else:
        print(f"\n✗ {result['message']}")
    
    input("\nPress Enter to continue...")