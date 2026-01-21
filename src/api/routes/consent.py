"""Privacy consent endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from consent.consent_storage import ConsentStorage

router = APIRouter()


class ConsentRequest(BaseModel):
    """Request model for privacy consent."""
    consent_given: bool
    user_id: Optional[str] = "default_user"


@router.post("/privacy-consent")
async def post_privacy_consent(request: ConsentRequest):
    """
    Store user privacy consent.
    
    Args:
        request: ConsentRequest containing consent_given boolean and optional user_id
        
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
            "message": "Consent stored successfully",
            "consent_given": request.consent_given,
            "user_id": request.user_id,
            "consent_status": consent_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing consent: {str(e)}"
        )
