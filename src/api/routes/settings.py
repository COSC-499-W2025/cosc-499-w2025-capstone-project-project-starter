"""Unified settings endpoints for account, privacy, and general preferences."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from consent.consent_storage import ConsentStorage
from database.user_preferences import (
    update_user_git_username,
    get_user_git_username
)
from database.user_informations import get_user_by_username
from api.schemas.auth import UserInfo, LoginResponse
from api.dependencies import get_authenticated_user

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


class GeneralSettingsRequest(BaseModel):
    """Request model for general settings."""
    git_username: Optional[str] = None


class AccountUpdateRequest(BaseModel):
    """Request model for account updates (placeholder for future use)."""
    pass


@router.get("")
async def get_all_settings(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Get all user settings (account, privacy, and general) for the authenticated user.
    
    Returns:
        dict: All user settings combined
    """
    try:
        username = current_user['user_name']
        user_id = str(current_user['user_id'])
        
        settings = {
            "success": True,
            "account": _user_data_to_dict(current_user),
            "privacy": None,
            "general": None
        }
        
        # Get privacy consent status using user_name
        consent_status = ConsentStorage.get_consent_status(username)
        settings["privacy"] = consent_status
        
        # Get general settings (note: get_user_git_username uses user_id=1, may need user-specific version)
        git_username = get_user_git_username()
        settings["general"] = {
            "git_username": git_username
        }
        
        return settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving settings: {str(e)}"
        )


@router.get("/account")
async def get_account_settings(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Get account/user information for the authenticated user.
    
    Returns:
        dict: Account information
    """
    try:
        return {
            "success": True,
            "account": _user_data_to_dict(current_user)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving account settings: {str(e)}"
        )


@router.post("/account")
async def update_account_settings(
    request: AccountUpdateRequest,
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Update account information (placeholder for future enhancements).
    
    Args:
        request: AccountUpdateRequest (currently unused)
        current_user: Authenticated user (from dependency)
        
    Returns:
        dict: Success message
    """
    return {
        "success": True,
        "message": "Account update feature coming soon"
    }


@router.get("/privacy")
async def get_privacy_settings(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Get privacy consent status for the authenticated user.
    
    Returns:
        dict: Privacy consent status
    """
    try:
        username = current_user['user_name']
        consent_status = ConsentStorage.get_consent_status(username)
        return {
            "success": True,
            "privacy": consent_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving privacy settings: {str(e)}"
        )


@router.post("/privacy")
async def update_privacy_settings(
    request: PrivacyConsentRequest,
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Update privacy consent for the authenticated user.
    
    Args:
        request: PrivacyConsentRequest containing consent_given boolean
        current_user: Authenticated user (from dependency)
        
    Returns:
        dict: Success message and consent status
    """
    try:
        username = current_user['user_name']
        success = ConsentStorage.store_consent(
            consent_given=request.consent_given,
            user_name=username
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to store consent in database"
            )
        
        # Get the updated consent status
        consent_status = ConsentStorage.get_consent_status(username)
        
        return {
            "success": True,
            "message": "Privacy consent updated successfully",
            "consent_given": request.consent_given,
            "user_name": username,
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
async def get_general_settings(
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Get general settings (git_username, etc.) for the authenticated user.
    
    Returns:
        dict: General settings
    """
    try:
        # Note: get_user_git_username() currently uses user_id=1
        # This may need to be updated to be user-specific
        git_username = get_user_git_username()
        return {
            "success": True,
            "general": {
                "git_username": git_username
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving general settings: {str(e)}"
        )


@router.post("/general")
async def update_general_settings(
    request: GeneralSettingsRequest,
    current_user: dict = Depends(get_authenticated_user)
):
    """
    Update general settings (git_username, etc.) for the authenticated user.
    
    Args:
        request: GeneralSettingsRequest containing settings to update
        current_user: Authenticated user (from dependency)
        
    Returns:
        dict: Success message and updated settings
    """
    try:
        if request.git_username is not None:
            # Note: update_user_git_username() currently uses user_id=1
            # This may need to be updated to be user-specific
            update_user_git_username(request.git_username)
        
        git_username = get_user_git_username()
        
        return {
            "success": True,
            "message": "General settings updated successfully",
            "general": {
                "git_username": git_username
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating general settings: {str(e)}"
        )
