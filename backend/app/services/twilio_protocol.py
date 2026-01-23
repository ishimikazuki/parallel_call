"""Twilio service protocol definition."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class CallStatus(str, Enum):
    """Twilio call statuses."""

    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


class AMDResult(str, Enum):
    """Answering Machine Detection results."""

    HUMAN = "human"
    MACHINE_START = "machine_start"
    MACHINE_END_BEEP = "machine_end_beep"
    MACHINE_END_SILENCE = "machine_end_silence"
    MACHINE_END_OTHER = "machine_end_other"
    FAX = "fax"
    UNKNOWN = "unknown"


@dataclass
class CallResult:
    """Result of a call initiation."""

    call_sid: str
    status: CallStatus
    to: str
    from_: str


@dataclass
class Conference:
    """Conference room info."""

    sid: str
    friendly_name: str
    status: str


class TwilioServiceProtocol(Protocol):
    """Protocol for Twilio service implementations."""

    async def make_call(
        self,
        to: str,
        from_: str,
        status_callback_url: str | None = None,
        machine_detection: bool = True,
    ) -> CallResult:
        """
        Initiate an outbound call.

        Args:
            to: Destination phone number (E.164 format)
            from_: Caller ID phone number (E.164 format)
            status_callback_url: URL to receive call status updates
            machine_detection: Enable AMD (Answering Machine Detection)

        Returns:
            CallResult with call SID and initial status
        """
        ...

    async def create_conference(self, friendly_name: str) -> Conference:
        """
        Create a conference room.

        Args:
            friendly_name: Human-readable name for the conference

        Returns:
            Conference info with SID
        """
        ...

    async def add_participant_to_conference(
        self,
        conference_sid: str,
        call_sid: str,
        muted: bool = False,
        hold: bool = False,
    ) -> None:
        """
        Add a call to a conference.

        Args:
            conference_sid: Conference room SID
            call_sid: Call SID to add
            muted: Start participant muted
            hold: Start participant on hold
        """
        ...

    async def hangup_call(self, call_sid: str) -> None:
        """
        Hang up a call.

        Args:
            call_sid: Call SID to hang up
        """
        ...

    async def get_call_status(self, call_sid: str) -> CallStatus:
        """
        Get current status of a call.

        Args:
            call_sid: Call SID to check

        Returns:
            Current CallStatus
        """
        ...
