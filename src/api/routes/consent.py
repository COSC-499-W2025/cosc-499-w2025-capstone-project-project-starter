"""Privacy consent endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from consent.consent_storage import ConsentStorage

router = APIRouter()


class ConsentRequest(BaseModel):
    """Request model for privacy consent."""
    consent_given: bool
    user_name: Optional[str] = None


@router.post("/privacy-consent")
async def post_privacy_consent(request: ConsentRequest):
    """
    Store user privacy consent.
    
    Args:
        request: ConsentRequest containing consent_given boolean and optional user_name
        
    Returns:
        dict: Success message and consent status
    """
    try:
        # Use provided user_name or get from AuthManager
        from account.user_manager import AuthManager
        user_name = request.user_name
        if user_name is None:
            user_name = AuthManager.get_current_username()
            if user_name is None:
                raise HTTPException(
                    status_code=400,
                    detail="No user_name provided and no user is logged in"
                )
        
        success = ConsentStorage.store_consent(
            consent_given=request.consent_given,
            user_name=user_name
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to store consent in database"
            )
        
        # Get the updated consent status
        consent_status = ConsentStorage.get_consent_status(user_name)
        
        return {
            "success": True,
            "message": "Consent stored successfully",
            "consent_given": request.consent_given,
            "user_name": user_name,
            "consent_status": consent_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing consent: {str(e)}"
        )
