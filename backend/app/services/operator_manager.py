"""Operator management service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OperatorStatus(str, Enum):
    """Operator availability status."""

    OFFLINE = "offline"  # ログアウト状態
    AVAILABLE = "available"  # 待機中（通話受付可能）
    ON_CALL = "on_call"  # 通話中
    ON_BREAK = "on_break"  # 休憩中
    WRAP_UP = "wrap_up"  # 後処理中


@dataclass
class OperatorSession:
    """
    Operator session state.

    Represents an operator's current session and status.
    """

    id: str
    name: str
    status: OperatorStatus = OperatorStatus.OFFLINE

    # Current call info
    current_call_sid: str | None = None
    current_lead_id: str | None = None

    # Timing
    _idle_since: datetime | None = field(default=None, repr=False)
    _call_started_at: datetime | None = field(default=None, repr=False)
    session_started_at: datetime | None = None

    # Stats for this session
    calls_handled: int = 0
    total_talk_time_seconds: int = 0

    @property
    def idle_since(self) -> datetime | None:
        """Get the time when operator became idle."""
        return self._idle_since

    @property
    def idle_duration_seconds(self) -> float:
        """Get how long operator has been idle."""
        if self._idle_since is None:
            return 0.0
        return (datetime.now(UTC) - self._idle_since).total_seconds()

    def go_online(self) -> None:
        """Set operator to available status."""
        self.status = OperatorStatus.AVAILABLE
        self._idle_since = datetime.now(UTC)
        self.session_started_at = datetime.now(UTC)

    def go_offline(self) -> None:
        """Set operator to offline status."""
        self.status = OperatorStatus.OFFLINE
        self._idle_since = None
        self.current_call_sid = None
        self.current_lead_id = None

    def start_call(self, call_sid: str, lead_id: str) -> None:
        """
        Start a call for this operator.

        Args:
            call_sid: The Twilio call SID
            lead_id: The lead being called
        """
        self.status = OperatorStatus.ON_CALL
        self.current_call_sid = call_sid
        self.current_lead_id = lead_id
        self._call_started_at = datetime.now(UTC)
        self._idle_since = None

    def end_call(self) -> None:
        """End the current call and return to available."""
        if self._call_started_at:
            call_duration = (datetime.now(UTC) - self._call_started_at).total_seconds()
            self.total_talk_time_seconds += int(call_duration)
            self.calls_handled += 1

        self.status = OperatorStatus.AVAILABLE
        self.current_call_sid = None
        self.current_lead_id = None
        self._call_started_at = None
        self._idle_since = datetime.now(UTC)

    def go_on_break(self) -> None:
        """Set operator to break status."""
        self.status = OperatorStatus.ON_BREAK
        self._idle_since = None

    def return_from_break(self) -> None:
        """Return from break to available status."""
        self.status = OperatorStatus.AVAILABLE
        self._idle_since = datetime.now(UTC)

    def start_wrap_up(self) -> None:
        """Start wrap-up time after a call."""
        self.status = OperatorStatus.WRAP_UP
        self._idle_since = None

    def end_wrap_up(self) -> None:
        """End wrap-up and return to available."""
        self.status = OperatorStatus.AVAILABLE
        self._idle_since = datetime.now(UTC)

    def is_available(self) -> bool:
        """Check if operator can receive calls."""
        return self.status == OperatorStatus.AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "current_call_sid": self.current_call_sid,
            "current_lead_id": self.current_lead_id,
            "idle_duration_seconds": self.idle_duration_seconds,
            "calls_handled": self.calls_handled,
            "total_talk_time_seconds": self.total_talk_time_seconds,
        }


class OperatorManager:
    """
    Manages operator sessions and call routing.

    Responsibilities:
    - Track all operator sessions and their statuses
    - Select the best operator for incoming calls (longest idle)
    - Assign calls to operators
    - Track operator statistics
    - Alert on long idle times
    """

    def __init__(self, max_idle_seconds: int = 300):
        """
        Initialize the operator manager.

        Args:
            max_idle_seconds: Threshold for long idle alerts (default 5 min)
        """
        self._operators: dict[str, OperatorSession] = {}
        self.max_idle_seconds = max_idle_seconds

    def add_operator(self, operator: OperatorSession) -> None:
        """Add an operator to the manager."""
        self._operators[operator.id] = operator

    def remove_operator(self, operator_id: str) -> OperatorSession | None:
        """Remove an operator from the manager."""
        return self._operators.pop(operator_id, None)

    def get_operator(self, operator_id: str) -> OperatorSession | None:
        """Get an operator by ID."""
        return self._operators.get(operator_id)

    def get_all_operators(self) -> list[OperatorSession]:
        """Get all operators."""
        return list(self._operators.values())

    def get_available_operators(self) -> list[OperatorSession]:
        """Get all available operators."""
        return [op for op in self._operators.values() if op.is_available()]

    @property
    def available_count(self) -> int:
        """Count of available operators."""
        return len(self.get_available_operators())

    @property
    def on_call_count(self) -> int:
        """Count of operators on calls."""
        return len([op for op in self._operators.values() if op.status == OperatorStatus.ON_CALL])

    @property
    def offline_count(self) -> int:
        """Count of offline operators."""
        return len([op for op in self._operators.values() if op.status == OperatorStatus.OFFLINE])

    @property
    def on_break_count(self) -> int:
        """Count of operators on break."""
        return len([op for op in self._operators.values() if op.status == OperatorStatus.ON_BREAK])

    def select_operator(self) -> OperatorSession | None:
        """
        Select the best available operator for a call.

        Uses longest-idle-first strategy to ensure fair distribution.

        Returns:
            The selected operator, or None if no one is available
        """
        available = self.get_available_operators()
        if not available:
            return None

        # Sort by idle time descending (longest first)
        available.sort(key=lambda op: op.idle_duration_seconds, reverse=True)
        return available[0]

    def assign_call(
        self,
        operator_id: str,
        call_sid: str,
        lead_id: str,
    ) -> bool:
        """
        Assign a call to a specific operator.

        Args:
            operator_id: The operator to assign to
            call_sid: The call SID
            lead_id: The lead ID

        Returns:
            True if assigned successfully, False if operator not available
        """
        operator = self._operators.get(operator_id)
        if not operator or not operator.is_available():
            return False

        operator.start_call(call_sid, lead_id)
        return True

    def end_call(self, operator_id: str) -> bool:
        """
        End the call for an operator.

        Args:
            operator_id: The operator whose call ended

        Returns:
            True if ended successfully
        """
        operator = self._operators.get(operator_id)
        if not operator:
            return False

        operator.end_call()
        return True

    def get_long_idle_operators(self) -> list[OperatorSession]:
        """
        Get operators who have been idle too long.

        Returns:
            List of operators exceeding max idle time
        """
        long_idle = []
        for operator in self._operators.values():
            if operator.status == OperatorStatus.AVAILABLE:
                if operator.idle_duration_seconds > self.max_idle_seconds:
                    long_idle.append(operator)
        return long_idle

    def get_stats(self) -> dict[str, Any]:
        """Get overall operator statistics."""
        total = len(self._operators)
        return {
            "total": total,
            "available": self.available_count,
            "on_call": self.on_call_count,
            "on_break": self.on_break_count,
            "offline": self.offline_count,
            "utilization": self.on_call_count / max(1, total - self.offline_count),
        }

    def find_operator_by_call(self, call_sid: str) -> OperatorSession | None:
        """Find the operator handling a specific call."""
        for operator in self._operators.values():
            if operator.current_call_sid == call_sid:
                return operator
        return None
