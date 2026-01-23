"""Service dependencies for FastAPI dependency injection."""

from functools import lru_cache

from app.config import get_settings
from app.services.twilio_mock import MockTwilioService
from app.services.twilio_protocol import TwilioServiceProtocol
from app.services.twilio_service import TwilioService


@lru_cache
def get_twilio_service() -> TwilioServiceProtocol:
    """
    Get Twilio service instance.

    Returns MockTwilioService in development or TwilioService in production,
    based on the TWILIO_USE_MOCK setting.
    """
    settings = get_settings()

    if settings.twilio_use_mock:
        return MockTwilioService()
    else:
        return TwilioService()
