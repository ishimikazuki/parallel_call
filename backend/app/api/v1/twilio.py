"""Twilio helper endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from app.api.v1.auth import get_current_user
from app.config import get_settings
from app.schemas.twilio import TwilioTokenResponse

router = APIRouter(prefix="/twilio", tags=["twilio"])


@router.post("/token", response_model=TwilioTokenResponse)
async def create_twilio_token(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> TwilioTokenResponse:
    """
    Create a Twilio Voice access token for the frontend SDK.

    Requires TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_APP_SID.
    """
    settings = get_settings()
    if not (
        settings.twilio_account_sid
        and settings.twilio_api_key_sid
        and settings.twilio_api_key_secret
        and settings.twilio_app_sid
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twilio credentials not configured",
        )

    identity = str(current_user.get("id") or current_user.get("username") or "operator")
    token = AccessToken(
        settings.twilio_account_sid,
        settings.twilio_api_key_sid,
        settings.twilio_api_key_secret,
        identity=identity,
    )
    token.add_grant(
        VoiceGrant(
            outgoing_application_sid=settings.twilio_app_sid,
            incoming_allow=True,
        )
    )

    return TwilioTokenResponse(token=token.to_jwt().decode("utf-8"), identity=identity)
