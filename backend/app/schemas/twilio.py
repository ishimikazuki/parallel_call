"""Twilio API schemas."""

from pydantic import BaseModel


class TwilioTokenResponse(BaseModel):
    """Twilio Voice access token response."""

    token: str
    identity: str
