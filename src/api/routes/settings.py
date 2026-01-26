"""Unified settings endpoints for account, privacy, and general preferences."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from consent.consent_storage import ConsentStorage
from database.user_preferences import (
    update_user_git_username,
    get_user_git_username
)
from database.user_informations import get_user_by_username
from api.schemas.auth import UserInfo, LoginResponse

router = APIRouter()


def _user_data_to_dict(user_data: dict) -> dict:
    """Convert user database data to UserInfo and then to dict format."""
    user_info = UserInfo(
        user_id=user_data['user_id'],
        user_name=user_data['user_name'],
        create_time=user_data.get('create_time'),
        last_login_time=user_data.get('last_login_time'),
        is_login=user_data.get('is_login', False)
    )
    return {
        "user_id": user_info.user_id,
        "user_name": user_info.user_name,
        "create_time": user_info.create_time.isoformat() if user_info.create_time else None,
        "last_login_time": user_info.last_login_time.isoformat() if user_info.last_login_time else None,
        "is_login": user_info.is_login
    }


class PrivacyConsentRequest(BaseModel):
    """Request model for privacy consent."""
    consent_given: bool
    user_id: Optional[str] = "default_user"


class GeneralSettingsRequest(BaseModel):
    """Request model for general settings."""
    git_username: Optional[str] = None


class AccountUpdateRequest(BaseModel):
    """Request model for account updates (placeholder for future use)."""
    pass


@router.get("")
async def get_all_settings(
    username: Optional[str] = Query(None, description="Username to retrieve settings for")
):
    """
    Get all user settings (account, privacy, and general).
    
    Args:
        username: Optional username (required for account info)
        
    Returns:
        dict: All user settings combined
    """
    try:
        settings = {
            "success": True,
            "account": None,
            "privacy": None,
            "general": None
        }
        
        # Get account info if username provided
        if username:
            user_data = get_user_by_username(username.strip())
            if user_data:
                settings["account"] = _user_data_to_dict(user_data)
        
        # Get privacy consent status
        user_id = username or "default_user"
        consent_status = ConsentStorage.get_consent_status(user_id)
        settings["privacy"] = consent_status
        
        # Get general settings
        git_username = get_user_git_username()
        settings["general"] = {
            "git_username": git_username
        }
        
        return settings
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving settings: {str(e)}"
        )


@router.get("/account")
async def get_account_settings(
    username: str = Query(..., description="Username to retrieve account info for")
):
    """
    Get account/user information.
    
    Args:
        username: Username to retrieve account info for
        
    Returns:
        dict: Account information
    """
    try:
        if not username or not username.strip():
            raise HTTPException(
                status_code=400,
                detail="Username parameter is required"
            )
        
        user_data = get_user_by_username(username.strip())
        
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return {
            "success": True,
            "account": _user_data_to_dict(user_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving account settings: {str(e)}"
        )


@router.post("/account")
async def update_account_settings(request: AccountUpdateRequest):
    """
    Update account information (placeholder for future enhancements).
    
    Args:
        request: AccountUpdateRequest (currently unused)
        
    Returns:
        dict: Success message
    """
    return {
        "success": True,
        "message": "Account update feature coming soon"
    }


@router.get("/privacy")
async def get_privacy_settings(
    user_id: Optional[str] = Query("default_user", description="User ID to retrieve privacy consent for")
):
    """
    Get privacy consent status.
    
    Args:
        user_id: User ID to retrieve consent status for
        
    Returns:
        dict: Privacy consent status
    """
    try:
        consent_status = ConsentStorage.get_consent_status(user_id)
        return {
            "success": True,
            "privacy": consent_status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving privacy settings: {str(e)}"
        )


@router.post("/privacy")
async def update_privacy_settings(request: PrivacyConsentRequest):
    """
    Update privacy consent.
    
    Args:
        request: PrivacyConsentRequest containing consent_given boolean and optional user_id
        
    Returns:
        dict: Success message and consent status
    """
    try:
        success = ConsentStorage.store_consent(
            consent_given=request.consent_given,
            user_id=request.user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to store consent in database"
            )
        
        # Get the updated consent status
        consent_status = ConsentStorage.get_consent_status(request.user_id)
        
        return {
            "success": True,
            "message": "Privacy consent updated successfully",
            "consent_given": request.consent_given,
            "user_id": request.user_id,
            "privacy": consent_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating privacy settings: {str(e)}"
        )


@router.get("/general")
async def get_general_settings():
    """
    Get general settings (git_username, etc.).
    
    Returns:
        dict: General settings
    """
    try:
        git_username = get_user_git_username()
        return {
            "success": True,
            "general": {
                "git_username": git_username
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving general settings: {str(e)}"
        )


@router.post("/general")
async def update_general_settings(request: GeneralSettingsRequest):
    """
    Update general settings (git_username, etc.).
    
    Args:
        request: GeneralSettingsRequest containing settings to update
        
    Returns:
        dict: Success message and updated settings
    """
    try:
        if request.git_username is not None:
            update_user_git_username(request.git_username)
        
        git_username = get_user_git_username()
        
        return {
            "success": True,
            "message": "General settings updated successfully",
            "general": {
                "git_username": git_username
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating general settings: {str(e)}"
        )
