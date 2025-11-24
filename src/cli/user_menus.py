"""User account menu handlers for CLI interactions."""
import os
import sys
from account.user_manager import AuthManager

# Password display configuration
# Set to True for asterisks (*), False for visible password
SHOW_PASSWORD_AS_ASTERISK = True


def get_password_input(prompt="Password: ", show_asterisk=None):
    """
    Get password input with visual feedback.
    
    Args:
        prompt (str): The prompt to display
        show_asterisk (bool): If True, show asterisks; if False, show actual characters;
                             if None, use global setting
    
    Returns:
        str: The entered password
    """
    if show_asterisk is None:
        show_asterisk = SHOW_PASSWORD_AS_ASTERISK
        
    print(prompt, end="", flush=True)
    password = ""
    
    try:
        import msvcrt  # Windows
        
        while True:
            char = msvcrt.getch()
            
            # Handle Enter key
            if char == b'\r':
                print()  # New line
                break
            # Handle Backspace
            elif char == b'\x08':
                if password:
                    password = password[:-1]
                    print('\b \b', end="", flush=True)
            # Handle Ctrl+C
            elif char == b'\x03':
                print()
                raise KeyboardInterrupt
            # Handle normal characters
            else:
                try:
                    char_str = char.decode('utf-8')
                    if char_str.isprintable():
                        password += char_str
                        if show_asterisk:
                            print('*', end="", flush=True)
                        else:
                            print(char_str, end="", flush=True)
                except UnicodeDecodeError:
                    pass
                    
    except ImportError:
        # Unix/Linux/Mac fallback
        try:
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                tty.setraw(fd)
                
                while True:
                    char = sys.stdin.read(1)
                    
                    # Handle Enter key (newline)
                    if char == '\n' or char == '\r':
                        print()  # New line
                        break
                    # Handle Backspace (DEL key in terminal)
                    elif ord(char) == 127 or ord(char) == 8:
                        if password:
                            password = password[:-1]
                            print('\b \b', end="", flush=True)
                    # Handle Ctrl+C
                    elif ord(char) == 3:
                        print()
                        raise KeyboardInterrupt
                    # Handle normal printable characters
                    elif char.isprintable():
                        password += char
                        if show_asterisk:
                            print('*', end="", flush=True)
                        else:
                            print(char, end="", flush=True)
                            
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
        except (ImportError, AttributeError):
            # Final fallback for systems without termios
            try:
                import getpass
                print("\n[Using secure input - no visual feedback]")
                password = getpass.getpass("")
            except (ImportError, Exception):
                print("\n[Note: Password will be visible on this system]")
                password = input("")
    
    return password


def set_password_display_mode():
    """Allow user to choose password display mode."""
    global SHOW_PASSWORD_AS_ASTERISK
    
    print("\n" + "-"*40)
    print("PASSWORD DISPLAY SETTINGS")
    print("-"*40)
    print("Current mode:", "Asterisks (*)" if SHOW_PASSWORD_AS_ASTERISK else "Visible characters")
    print("\nChoose password display mode:")
    print("1. Show asterisks (*) when typing")
    print("2. Show actual characters when typing")
    print("3. Keep current setting")
    
    choice = input("\nChoose an option (1-3): ").strip()
    
    if choice == '1':
        SHOW_PASSWORD_AS_ASTERISK = True
        print("Password display set to asterisks (*)")
    elif choice == '2':
        SHOW_PASSWORD_AS_ASTERISK = False
        print("Password display set to visible characters")
    elif choice == '3':
        print("Keeping current setting")
    else:
        print("Invalid choice. Keeping current setting.")
    
    input("\nPress Enter to continue...")


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
            print("2. Password display settings")
            print("3. Back to main menu")
            print("="*50)
            
            choice = input("Choose an option (1-3): ").strip()
            
            if choice == '1':
                handle_user_logout()
            elif choice == '2':
                set_password_display_mode()
            elif choice == '3':
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        else:
            # User is not logged in - show login and register options
            print("You are not currently logged in.")
            print("\nOptions:")
            print("1. Login to existing account")
            print("2. Create new account")
            print("3. Password display settings")
            print("4. Back to main menu")
            print("="*50)
            
            choice = input("Choose an option (1-4): ").strip()
            
            if choice == '1':
                handle_user_login()
            elif choice == '2':
                handle_user_registration()
            elif choice == '3':
                set_password_display_mode()
            elif choice == '4':
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")


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
        password = get_password_input("Password: ")
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
        return
    
    if not password:
        print("Password cannot be empty.")
        return
    
    result = AuthManager.login(username, password)
    
    if result['success']:
        print(f"\n[SUCCESS] {result['message']}")
        print(f"Welcome back, {username}!")
        input("\nPress Enter to continue...")
    else:
        print(f"\n[ERROR] {result['message']}")
        input("\nPress Enter to continue...")


def handle_user_logout():
    """Handle user logout process."""
    current_user = AuthManager.get_current_username()
    
    confirm = input(f"Are you sure you want to logout from '{current_user}'? (y/n): ").strip().lower()
    
    if confirm in ('y', 'yes'):
        result = AuthManager.logout()
        
        if result['success']:
            print(f"\n[SUCCESS] {result['message']}")
            print("You have been logged out.")
        else:
            print(f"\n[ERROR] {result['message']}")
        
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
        password = get_password_input("Choose a password (minimum 6 characters): ")
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return
    
    if not password:
        print("Password cannot be empty.")
        return
    
    try:
        confirm_password = get_password_input("Confirm password: ")
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return
    
    if password != confirm_password:
        print("Passwords do not match.")
        return
    
    result = AuthManager.register(username, password)
    
    if result['success']:
        print(f"\n[SUCCESS] {result['message']}")
        print(f"Account created successfully! User ID: {result['user_id']}")
        
        # Ask if user wants to login immediately
        login_now = input("\nWould you like to login now? (y/n): ").strip().lower()
        if login_now in ('y', 'yes'):
            login_result = AuthManager.login(username, password)
            if login_result['success']:
                print(f"\n[SUCCESS] {login_result['message']}")
                print(f"Welcome, {username}!")
    else:
        print(f"\n[ERROR] {result['message']}")
    
    input("\nPress Enter to continue...")