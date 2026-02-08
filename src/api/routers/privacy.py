from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_config_manager
from src.config.config_manager import UserConfigManager

router = APIRouter(tags=["privacy"])


class PrivacyConsentRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    zip_path: str = Field(..., min_length=1)
    llm_consent: bool
    data_access_consent: Optional[bool] = None


@router.post("/privacy-consent")
def set_privacy_consent(
    payload: PrivacyConsentRequest,
    manager: UserConfigManager = Depends(get_config_manager),
):
    user_id = payload.user_id.strip()
    zip_path = payload.zip_path.strip()
    if not user_id or not zip_path:
        raise HTTPException(status_code=400, detail="user_id and zip_path are required")

    existing = manager.load_config(user_id, silent=True)
    if existing:
        updated = manager.update_config(
            user_id,
            zip_file=zip_path,
            llm_consent=payload.llm_consent,
            llm_consent_asked=True,
            data_access_consent=payload.data_access_consent,
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update consent")
        data_access_consent = (
            payload.data_access_consent
            if payload.data_access_consent is not None
            else existing.data_access_consent
        )
    else:
        data_access_consent = payload.data_access_consent if payload.data_access_consent is not None else False
        created = manager.create_config(
            user_id,
            zip_path,
            payload.llm_consent,
            llm_consent_asked=True,
            data_access_consent=data_access_consent,
        )
        if not created:
            raise HTTPException(status_code=500, detail="Failed to store consent")

    return {
        "status": "ok",
        "user_id": user_id,
        "zip_path": zip_path,
        "llm_consent": payload.llm_consent,
        "data_access_consent": data_access_consent,
    }
