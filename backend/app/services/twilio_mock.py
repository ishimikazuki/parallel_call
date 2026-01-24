"""Mock Twilio service for development and testing."""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from app.services.twilio_protocol import (
    AMDResult,
    CallResult,
    CallStatus,
    Conference,
    TwilioServiceProtocol,
)


@dataclass
class MockCall:
    """Internal representation of a mock call."""

    call_sid: str
    to: str
    from_: str
    status: CallStatus = CallStatus.QUEUED
    amd_result: AMDResult | None = None
    conference_sid: str | None = None


@dataclass
class MockConference:
    """Internal representation of a mock conference."""

    sid: str
    friendly_name: str
    status: str = "init"
    participants: list[str] = field(default_factory=list)


class MockTwilioService(TwilioServiceProtocol):
    """
    Mock implementation of Twilio service.

    Simulates Twilio API behavior for development without a real account.
    Can be configured to simulate various scenarios (busy, no-answer, etc.)
    """

    def __init__(
        self,
        default_amd_result: AMDResult = AMDResult.HUMAN,
        call_answer_delay: float = 1.0,
        amd_detection_delay: float = 2.0,
    ):
        """
        Initialize mock service.

        Args:
            default_amd_result: Default AMD result for calls
            call_answer_delay: Seconds before call is "answered"
            amd_detection_delay: Seconds before AMD result is available
        """
        self.default_amd_result = default_amd_result
        self.call_answer_delay = call_answer_delay
        self.amd_detection_delay = amd_detection_delay

        self._calls: dict[str, MockCall] = {}
        self._conferences: dict[str, MockConference] = {}

        # Callbacks for status changes (for webhook simulation)
        self._status_callbacks: list[Callable[[str, CallStatus], None]] = []
        self._amd_callbacks: list[Callable[[str, AMDResult], None]] = []

    def _generate_sid(self, prefix: str) -> str:
        """Generate a Twilio-like SID."""
        return f"{prefix}{uuid.uuid4().hex[:32]}"

    async def make_call(
        self,
        to: str,
        from_: str,
        status_callback_url: str | None = None,
        machine_detection: bool = True,
    ) -> CallResult:
        """Initiate a mock call."""
        call_sid = self._generate_sid("CA")

        mock_call = MockCall(
            call_sid=call_sid,
            to=to,
            from_=from_,
            status=CallStatus.QUEUED,
        )
        self._calls[call_sid] = mock_call

        # Simulate async call progression
        asyncio.create_task(self._simulate_call_progression(call_sid, machine_detection))

        return CallResult(
            call_sid=call_sid,
            status=CallStatus.QUEUED,
            to=to,
            from_=from_,
        )

    async def _simulate_call_progression(self, call_sid: str, machine_detection: bool) -> None:
        """Simulate the progression of a call through various states."""
        call = self._calls.get(call_sid)
        if not call:
            return

        # Queued -> Ringing
        await asyncio.sleep(0.5)
        call.status = CallStatus.RINGING
        await self._notify_status_change(call_sid, CallStatus.RINGING)

        # Ringing -> In Progress (answered)
        await asyncio.sleep(self.call_answer_delay)
        call.status = CallStatus.IN_PROGRESS
        await self._notify_status_change(call_sid, CallStatus.IN_PROGRESS)

        # AMD detection
        if machine_detection:
            await asyncio.sleep(self.amd_detection_delay)
            call.amd_result = self.default_amd_result
            await self._notify_amd_result(call_sid, call.amd_result)

    async def _notify_status_change(self, call_sid: str, status: CallStatus) -> None:
        """Notify registered callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                callback(call_sid, status)
            except Exception:
                pass

    async def _notify_amd_result(self, call_sid: str, result: AMDResult) -> None:
        """Notify registered callbacks of AMD result."""
        for callback in self._amd_callbacks:
            try:
                callback(call_sid, result)
            except Exception:
                pass

    async def create_conference(self, friendly_name: str) -> Conference:
        """Create a mock conference."""
        sid = self._generate_sid("CF")

        mock_conference = MockConference(
            sid=sid,
            friendly_name=friendly_name,
            status="init",
        )
        self._conferences[sid] = mock_conference

        return Conference(
            sid=sid,
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
        """Add a call to a mock conference."""
        conference = self._conferences.get(conference_sid)
        call = self._calls.get(call_sid)

        if not conference:
            raise ValueError(f"Conference {conference_sid} not found")
        if not call:
            raise ValueError(f"Call {call_sid} not found")

        conference.participants.append(call_sid)
        call.conference_sid = conference_sid

        if len(conference.participants) > 0:
            conference.status = "in-progress"

    async def hangup_call(self, call_sid: str) -> None:
        """Hang up a mock call."""
        call = self._calls.get(call_sid)
        if call:
            call.status = CallStatus.COMPLETED
            await self._notify_status_change(call_sid, CallStatus.COMPLETED)

    async def get_call_status(self, call_sid: str) -> CallStatus:
        """Get status of a mock call."""
        call = self._calls.get(call_sid)
        if not call:
            raise ValueError(f"Call {call_sid} not found")
        return call.status

    # Test helper methods

    def register_status_callback(self, callback: Callable[[str, CallStatus], None]) -> None:
        """Register a callback for call status changes."""
        self._status_callbacks.append(callback)

    def register_amd_callback(self, callback: Callable[[str, AMDResult], None]) -> None:
        """Register a callback for AMD results."""
        self._amd_callbacks.append(callback)

    def set_next_call_outcome(
        self,
        status: CallStatus = CallStatus.IN_PROGRESS,
        amd_result: AMDResult = AMDResult.HUMAN,
    ) -> None:
        """Configure the outcome of the next call (for testing)."""
        self.default_amd_result = amd_result
        # Additional logic can be added to force specific outcomes

    def get_call(self, call_sid: str) -> MockCall | None:
        """Get a mock call by SID (for testing)."""
        return self._calls.get(call_sid)

    def get_conference(self, conference_sid: str) -> MockConference | None:
        """Get a mock conference by SID (for testing)."""
        return self._conferences.get(conference_sid)

    def reset(self) -> None:
        """Reset all mock data (for testing)."""
        self._calls.clear()
        self._conferences.clear()
