"""User account menu handlers for CLI interactions."""
import io
import os
import sys
from account.user_manager import AuthManager
from cli.cli_output import print_header, print_section, print_success, print_error, pause, safe_input, print_info

# Password display configuration
# Set to True for asterisks (*), False for visible password
SHOW_PASSWORD_AS_ASTERISK = True

# Menu item constants
LOGGED_IN_MENU_ITEMS = [
    "Logout",                      # 1
    "Password display settings",   # 2
    "Back to main menu"            # 3
]

LOGIN_MENU_ITEMS = [
    "Login to existing account",   # 1
    "Create new account",          # 2
    "Password display settings",   # 3
    "Back to main menu"            # 4
]

INITIAL_LOGIN_MENU_ITEMS = [
    "Login to existing account",   # 1
    "Create new account",          # 2
    "Password display settings",   # 3
    "Exit"                         # 4
]


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
        # Helper function to read password character by character
        def read_password_chars():
            """Read password characters, handling both TTY and non-TTY stdin."""
            nonlocal password
            while True:
                char = sys.stdin.read(1)
                if not char:  # EOF
                    break
                if char == '\n' or char == '\r':
                    print()  # New line
                    break
                elif ord(char) == 127 or ord(char) == 8:
                    if password:
                        password = password[:-1]
                        print('\b \b', end="", flush=True)
                elif ord(char) == 3:
                    print()
                    raise KeyboardInterrupt
                elif char.isprintable():
                    password += char
                    if show_asterisk:
                        print('*', end="", flush=True)
                    else:
                        print(char, end="", flush=True)
        
        try:
            import termios
            import tty
            
            # Try to use termios for raw mode (only works with real TTY)
            try:
                # Check if stdin is a TTY
                if not sys.stdin.isatty():
                    raise io.UnsupportedOperation("Not a TTY")
                
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                
                try:
                    tty.setraw(fd)
                    read_password_chars()
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    
            except (io.UnsupportedOperation, AttributeError, OSError):
                # Stdin is redirected (e.g., in tests) or termios failed
                # Use read() directly - this works with mocked stdin in tests
                read_password_chars()
                
        except ImportError:
            # termios not available, use read() directly
            read_password_chars()
    
    return password

def _safe_input(prompt: str, *, input_fn=input, default: str = "") -> str:
    """Input wrapper that won't crash tests when stdin is unavailable."""
    try:
        return input_fn(prompt)
    except EOFError:
        return default


def _pause(*, input_fn=input) -> None:
    """Press-enter pause that won't crash in tests."""
    try:
        input_fn("\nPress Enter to continue...")
    except EOFError:
        pass

def set_password_display_mode():
    global SHOW_PASSWORD_AS_ASTERISK

    print("\n" + "-" * 40)
    print("PASSWORD DISPLAY SETTINGS")
    print("-" * 40)
    print(
        "Current mode:",
        "Asterisks (*)" if SHOW_PASSWORD_AS_ASTERISK else "Visible characters",
    )
    print("\nChoose password display mode:")
    print("1. Show asterisks (*) when typing")
    print("2. Show actual characters when typing")
    print("3. Keep current setting")

    try:
        choice = input("\nChoose an option (1-3): ").strip()
    except EOFError:
        print("EOF detected. Keeping current setting.")
        return False

    if choice == "1":
        SHOW_PASSWORD_AS_ASTERISK = True
        print("Password display set to asterisks (*)")
        return True
    elif choice == "2":
        SHOW_PASSWORD_AS_ASTERISK = False
        print("Password display set to visible characters")
        return True
    elif choice == "3":
        print("Keeping current setting")
        return False
    else:
        print("Invalid choice. Keeping current setting.")
        return False



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
            for idx, label in enumerate(LOGGED_IN_MENU_ITEMS, start=1):
                print(f"{idx}. {label}")
            print("="*50)
            
            choice = input("Choose an option (1-3): ").strip()
            
            logged_in_handlers = {
                "1": lambda: handle_user_logout(),
                "2": lambda: set_password_display_mode(),
                "3": "BACK"
            }
            
            handler = logged_in_handlers.get(choice)
            
            if handler is None:
                print("Invalid choice. Please enter 1, 2, or 3.")
                continue
            
            if handler == "BACK":
                break
            
            handler()
        else:
            # User is not logged in - show login and register options
            print("You are not currently logged in.")
            print("\nOptions:")
            for idx, label in enumerate(LOGIN_MENU_ITEMS, start=1):
                print(f"{idx}. {label}")
            print("="*50)
            
            choice = input("Choose an option (1-4): ").strip()
            
            login_handlers = {
                "1": lambda: handle_user_login(),
                "2": lambda: handle_user_registration(),
                "3": lambda: set_password_display_mode(),
                "4": "BACK"
            }
            
            handler = login_handlers.get(choice)
            
            if handler is None:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
                continue
            
            if handler == "BACK":
                break
            
            handler()


def handle_user_login():
    print("\n" + "-" * 40)
    print("USER LOGIN")
    print("-" * 40)

    try:
        username = input("Username: ").strip()
    except EOFError:
        print("EOF detected. Login cancelled.")
        return None

    if not username:
        print("Username cannot be empty.")
        input("\nPress Enter to continue...")
        return None

    try:
        password = get_password_input("Password: ")
    except EOFError:
        print("EOF detected. Login cancelled.")
        return None
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
        return None

    if not password:
        print("Password cannot be empty.")
        input("\nPress Enter to continue...")
        return None

    result = AuthManager.login(username, password)

    if result.get("success"):
        print(f"\n[SUCCESS] {result.get('message')}")
        print(f"Welcome back, {username}!")
    else:
        print(f"\n[ERROR] {result.get('message')}")

    try:
        input("\nPress Enter to continue...")
    except EOFError:
        pass

    return result


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
    print("\n" + "-" * 40)
    print("CREATE NEW ACCOUNT")
    print("-" * 40)

    try:
        username = input("Choose a username: ").strip()
    except EOFError:
        print("EOF detected. Registration cancelled.")
        return None

    if not username:
        print("Username cannot be empty.")
        input("\nPress Enter to continue...")
        return None

    try:
        password = get_password_input("Choose a password (minimum 6 characters): ")
    except EOFError:
        print("EOF detected. Registration cancelled.")
        return None
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return None

    if not password:
        print("Password cannot be empty.")
        input("\nPress Enter to continue...")
        return None

    if len(password) < 6:
        print("Password must be at least 6 characters.")
        input("\nPress Enter to continue...")
        return None

    try:
        confirm_password = get_password_input("Confirm password: ")
    except EOFError:
        print("EOF detected. Registration cancelled.")
        return None
    except KeyboardInterrupt:
        print("\nRegistration cancelled.")
        return None

    if password != confirm_password:
        print("Passwords do not match.")
        input("\nPress Enter to continue...")
        return None

    result = AuthManager.register(username, password)

    if result.get("success"):
        print(f"\n[SUCCESS] {result.get('message')}")
        print(f"Account created successfully! User ID: {result.get('user_id')}")

        try:
            login_now = input("\nWould you like to login now? (y/n): ").strip().lower()
        except EOFError:
            print("EOF detected. Registration cancelled.")
            return result

        if login_now in ("y", "yes"):
            login_result = AuthManager.login(username, password)
            if login_result.get("success"):
                print(f"\n[SUCCESS] {login_result.get('message')}")
                print(f"Welcome, {username}!")
    else:
        print(f"\n[ERROR] {result.get('message')}")

    try:
        input("\nPress Enter to continue...")
    except EOFError:
        pass

    return result



def login_menu():
    """Display login menu for unauthenticated users."""
    while True:
        print("\n" + "="*70)
        print("MINING DIGITAL WORK ARTIFACTS - Login Required")
        print("="*70)
        print("Welcome! Please log in or create an account to continue.")
        print("\nOptions:")
        for idx, label in enumerate(INITIAL_LOGIN_MENU_ITEMS, start=1):
            print(f"{idx}. {label}")
        print("="*70)
        
        try:
            choice = input("Choose an option (1-4): ").strip()
        except EOFError:
            print("\nEOF detected. Exiting...")
            return False
        
        def handle_login_and_check():
            handle_user_login()
            # If login was successful, return True to continue to main menu
            if AuthManager.is_user_logged_in():
                return True
            return None
        
        def handle_registration_and_check():
            handle_user_registration()
            # If registration was successful and user logged in, return True
            if AuthManager.is_user_logged_in():
                return True
            return None
        
        def handle_exit():
            print("Goodbye!")
            return False
        
        initial_handlers = {
            "1": handle_login_and_check,
            "2": handle_registration_and_check,
            "3": lambda: set_password_display_mode(),
            "4": handle_exit
        }
        
        handler = initial_handlers.get(choice)
        
        if handler is None:
            print("Invalid choice. Please enter 1-4.")
            continue
        
        result = handler()
        if result is not None:  # True or False returned
            return result