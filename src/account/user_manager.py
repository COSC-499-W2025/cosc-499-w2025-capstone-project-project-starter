from database.user_informations import (
    create_user,
    login_user,
    logout_user,
    is_username_available,
    get_user_by_username
)
from typing import Dict, Any, Optional


class AuthManager:
    """
    User authentication manager class providing login, logout, and account registration functionality
    with local session tracking
    """
    
    # Class variable to track currently logged-in user
    _current_user = None
    
    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """
        Get the currently logged-in user information
        
        Returns:
            Optional[Dict[str, Any]]: Current user information or None if no user is logged in
        """
        return cls._current_user
    
    @classmethod
    def is_user_logged_in(cls) -> bool:
        """
        Check if any user is currently logged in locally
        
        Returns:
            bool: True if a user is logged in, False otherwise
        """
        return cls._current_user is not None
    
    @classmethod
    def get_current_username(cls) -> Optional[str]:
        """
        Get the username of the currently logged-in user
        
        Returns:
            Optional[str]: Current username or None if no user is logged in
        """
        return cls._current_user['user_name'] if cls._current_user else None
    
    @classmethod
    def clear_session(cls):
        """
        Clear the current session (for internal use)
        """
        cls._current_user = None

    @staticmethod
    def register(username: str, password: str) -> Dict[str, Any]:
        """
        Register a new user account
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            Dict[str, Any]: Dictionary containing registration result
                - success (bool): Whether registration was successful
                - message (str): Result message
                - user_id (Optional[int]): User ID returned on success
        """
        # Validate input
        if not username or not username.strip():
            return {
                'success': False,
                'message': 'Username cannot be empty',
                'user_id': None
            }
        
        if not password or len(password) < 6:
            return {
                'success': False,
                'message': 'Password must be at least 6 characters long',
                'user_id': None
            }
        
        # Check if username is available
        if not is_username_available(username):
            return {
                'success': False,
                'message': 'Username already exists',
                'user_id': None
            }
        
        # Create user
        user_id = create_user(username, password)
        if user_id:
            return {
                'success': True,
                'message': 'Registration successful',
                'user_id': user_id
            }
        else:
            return {
                'success': False,
                'message': 'Registration failed, please try again later',
                'user_id': None
            }

    @classmethod
    def login(cls, username: str, password: str) -> Dict[str, Any]:
        """
        User login with local session tracking
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            Dict[str, Any]: Dictionary containing login result
                - success (bool): Whether login was successful
                - message (str): Result message
                - user_info (Optional[Dict]): User information if login successful
        """
        # Check if someone is already logged in
        if cls.is_user_logged_in():
            return {
                'success': False,
                'message': f'User "{cls.get_current_username()}" is already logged in. Please logout first.',
                'user_info': None
            }
        
        # Validate input
        if not username or not username.strip():
            return {
                'success': False,
                'message': 'Username cannot be empty',
                'user_info': None
            }
        
        if not password:
            return {
                'success': False,
                'message': 'Password cannot be empty',
                'user_info': None
            }
        
        # Attempt login
        if login_user(username, password):
            # Get user information for local tracking
            user_info = get_user_by_username(username)
            if user_info:
                cls._current_user = user_info
                return {
                    'success': True,
                    'message': 'Login successful',
                    'user_info': user_info
                }
            else:
                return {
                    'success': False,
                    'message': 'Login failed: Unable to retrieve user information',
                    'user_info': None
                }
        else:
            return {
                'success': False,
                'message': 'Invalid username or password',
                'user_info': None
            }

    @classmethod
    def logout(cls, username: str = None) -> Dict[str, Any]:
        """
        User logout with local session clearing
        
        Args:
            username (str, optional): Username to logout. If None, logout current user
            
        Returns:
            Dict[str, Any]: Dictionary containing logout result
                - success (bool): Whether logout was successful
                - message (str): Result message
        """
        # If no username provided, use current logged-in user
        if username is None:
            if not cls.is_user_logged_in():
                return {
                    'success': False,
                    'message': 'No user is currently logged in'
                }
            username = cls.get_current_username()
        
        # Validate input
        if not username or not username.strip():
            return {
                'success': False,
                'message': 'Username cannot be empty'
            }
        
        # Check if the username matches current user
        current_username = cls.get_current_username()
        if current_username and username != current_username:
            return {
                'success': False,
                'message': f'Cannot logout "{username}". Currently logged in as "{current_username}"'
            }
        
        # Attempt logout
        if logout_user(username):
            cls.clear_session()  # Clear local session
            return {
                'success': True,
                'message': 'Logout successful'
            }
        else:
            return {
                'success': False,
                'message': 'Logout failed, user may not exist or is not logged in'
            }