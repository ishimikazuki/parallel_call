"""Real Twilio service implementation."""

from typing import Any

from twilio.rest import Client

from app.config import get_settings
from app.services.twilio_protocol import (
    CallResult,
    CallStatus,
    Conference,
    TwilioServiceProtocol,
)


class TwilioService(TwilioServiceProtocol):
    """
    Real Twilio service implementation.

    Uses the Twilio Python SDK to interact with the Twilio API.
    """

    def __init__(self) -> None:
        """Initialize with Twilio credentials from settings."""
        settings = get_settings()
        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self._from_number = settings.twilio_phone_number

    async def make_call(
        self,
        to: str,
        from_: str,
        status_callback_url: str | None = None,
        machine_detection: bool = True,
    ) -> CallResult:
        """Initiate an outbound call via Twilio."""
        settings = get_settings()
        call_params: dict[str, Any] = {
            "to": to,
            "from_": from_ or self._from_number,
        }

        if settings.twilio_app_sid:
            call_params["application_sid"] = settings.twilio_app_sid
        else:
            call_params["url"] = "http://demo.twilio.com/docs/voice.xml"  # TwiML instructions

        callback_url = status_callback_url
        if not callback_url and settings.public_base_url:
            callback_url = f"{settings.public_base_url.rstrip('/')}/webhooks/twilio/status"

        if callback_url:
            call_params["status_callback"] = callback_url
            call_params["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]

        if machine_detection:
            call_params["machine_detection"] = "DetectMessageEnd"
            call_params["async_amd"] = True
            if settings.public_base_url:
                call_params["async_amd_status_callback"] = (
                    f"{settings.public_base_url.rstrip('/')}/webhooks/twilio/amd"
                )

        call = self._client.calls.create(**call_params)

        return CallResult(
            call_sid=call.sid,
            status=CallStatus(call.status),
            to=to,
            from_=from_ or self._from_number,
        )

    async def create_conference(self, friendly_name: str) -> Conference:
        """Create a conference room via Twilio."""
        # Note: In Twilio, conferences are created implicitly when first participant joins
        # We'll return a placeholder that gets real SID when first call joins
        return Conference(
            sid="pending",
            friendly_name=friendly_name,
            status="init",
        )

    async def add_participant_to_conference(
        self,
        conference_sid: str,
        call_sid: str,
        muted: bool = False,
        hold: bool = False,
    ) -> None:
        """Add a participant to a conference."""
        # This would use TwiML to redirect the call to the conference
        # Implementation depends on your specific call flow
        pass

    async def hangup_call(self, call_sid: str) -> None:
        """Hang up a call via Twilio."""
        self._client.calls(call_sid).update(status="completed")

    async def get_call_status(self, call_sid: str) -> CallStatus:
        """Get call status from Twilio."""
        call = self._client.calls(call_sid).fetch()
        return CallStatus(call.status)
