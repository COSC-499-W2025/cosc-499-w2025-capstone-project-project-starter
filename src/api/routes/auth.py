"""Authentication endpoints for user login/logout."""
from fastapi import APIRouter, HTTPException, status
from api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    UserInfo,
)
from database.user_informations import (
    verify_password,
    login_user,
    logout_user,
    get_user_by_username,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate a user with username and password.
    
    Returns user information on success, error message on failure.
    """
    username = request.username.strip()
    password = request.password
    
    # Validate input
    if not username:
        return LoginResponse(
            success=False,
            message="Username cannot be empty",
            user=None
        )
    
    if not password:
        return LoginResponse(
            success=False,
            message="Password cannot be empty",
            user=None
        )
    
    # Attempt login using the existing database function
    if login_user(username, password):
        # Get user information
        user_data = get_user_by_username(username)
        if user_data:
            user_info = UserInfo(
                user_id=user_data['user_id'],
                user_name=user_data['user_name'],
                create_time=user_data.get('create_time'),
                last_login_time=user_data.get('last_login_time'),
                is_login=user_data.get('is_login', True)
            )
            return LoginResponse(
                success=True,
                message="Login successful",
                user=user_info
            )
        else:
            return LoginResponse(
                success=False,
                message="Login failed: Unable to retrieve user information",
                user=None
            )
    else:
        return LoginResponse(
            success=False,
            message="Invalid username or password",
            user=None
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest):
    """
    Logout a user by username.
    
    Updates the login status in the database.
    """
    username = request.username.strip()
    
    if not username:
        return LogoutResponse(
            success=False,
            message="Username cannot be empty"
        )
    
    # Check if user exists
    user_data = get_user_by_username(username)
    if not user_data:
        return LogoutResponse(
            success=False,
            message=f"User '{username}' not found"
        )
    
    # Check if user is actually logged in
    if not user_data.get('is_login', False):
        return LogoutResponse(
            success=False,
            message=f"User '{username}' is not currently logged in"
        )
    
    # Attempt logout
    if logout_user(username):
        return LogoutResponse(
            success=True,
            message="Logout successful"
        )
    else:
        return LogoutResponse(
            success=False,
            message="Logout failed"
        )


@router.get("/me", response_model=LoginResponse)
async def get_current_user(username: str):
    """
    Get current user information by username.
    
    This is a simple endpoint that checks if a user exists and is logged in.
    For proper session management, JWT tokens should be implemented in a future PR.
    """
    if not username or not username.strip():
        return LoginResponse(
            success=False,
            message="Username parameter is required",
            user=None
        )
    
    user_data = get_user_by_username(username.strip())
    
    if not user_data:
        return LoginResponse(
            success=False,
            message="User not found",
            user=None
        )
    
    if not user_data.get('is_login', False):
        return LoginResponse(
            success=False,
            message="User is not logged in",
            user=None
        )
    
    user_info = UserInfo(
        user_id=user_data['user_id'],
        user_name=user_data['user_name'],
        create_time=user_data.get('create_time'),
        last_login_time=user_data.get('last_login_time'),
        is_login=user_data.get('is_login', False)
    )
    
    return LoginResponse(
        success=True,
        message="User is authenticated",
        user=user_info
    )
