"""Authentication request/response schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class UserInfo(BaseModel):
    """User information returned after successful authentication."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    user_name: str
    create_time: Optional[datetime] = None
    last_login_time: Optional[datetime] = None
    is_login: bool = False


class LoginResponse(BaseModel):
    """Response model for login attempts."""
    success: bool
    message: str
    user: Optional[UserInfo] = None


class LogoutRequest(BaseModel):
    """Request model for user logout."""
    username: str = Field(..., min_length=1, description="Username to logout")


class LogoutResponse(BaseModel):
    """Response model for logout attempts."""
    success: bool
    message: str
