"""Lead domain model."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class LeadStatus(str, Enum):
    """Lead status in the calling workflow."""

    PENDING = "pending"  # 未発信、発信待ち
    CALLING = "calling"  # 発信中
    CONNECTED = "connected"  # オペレーターと接続中
    COMPLETED = "completed"  # 通話完了
    FAILED = "failed"  # 発信失敗（busy, no_answer など）
    DNC = "dnc"  # Do Not Call - 発信禁止


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current_status: LeadStatus, attempted_action: str):
        self.current_status = current_status
        self.attempted_action = attempted_action
        super().__init__(
            f"Cannot {attempted_action} from status {current_status.value}"
        )


# E.164 format: + followed by 1-15 digits
E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


def validate_phone_number(phone: str) -> str:
    """Validate and return phone number in E.164 format."""
    if not phone:
        raise ValueError("Phone number is required")
    if not E164_PATTERN.match(phone):
        raise ValueError(f"Invalid phone number format: {phone}. Must be E.164 format (e.g., +818011112222)")
    return phone


@dataclass
class Lead:
    """
    Lead (見込み客) domain model.

    Represents a potential customer to be called in a campaign.
    Tracks status, call history, and outcomes.
    """

    phone_number: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None
    company: str | None = None
    email: str | None = None
    notes: str | None = None

    # Status tracking
    status: LeadStatus = LeadStatus.PENDING
    outcome: str | None = None
    fail_reason: str | None = None

    # Retry management
    retry_count: int = 0
    max_retries: int = 3

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_called_at: datetime | None = None

    # Call history
    call_history: list[dict[str, Any]] = field(default_factory=list)

    # Campaign association
    campaign_id: str | None = None

    def __post_init__(self) -> None:
        """Validate phone number on creation."""
        self.phone_number = validate_phone_number(self.phone_number)

    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def _can_transition_from(self, allowed_statuses: list[LeadStatus], action: str) -> None:
        """Check if transition is allowed from current status."""
        if self.status not in allowed_statuses:
            raise InvalidStatusTransitionError(self.status, action)

    def start_calling(self) -> None:
        """
        Transition to CALLING status.

        Only allowed from PENDING status.
        """
        self._can_transition_from([LeadStatus.PENDING], "start_calling")
        self.status = LeadStatus.CALLING
        self.last_called_at = datetime.now(timezone.utc)
        self._update_timestamp()

    def connect(self) -> None:
        """
        Transition to CONNECTED status.

        Only allowed from CALLING status (after AMD detects human).
        """
        self._can_transition_from([LeadStatus.CALLING], "connect")
        self.status = LeadStatus.CONNECTED
        self._update_timestamp()

    def complete(self, outcome: str) -> None:
        """
        Transition to COMPLETED status with an outcome.

        Only allowed from CONNECTED status.

        Args:
            outcome: Result of the call (e.g., "interested", "not_interested", "callback")
        """
        self._can_transition_from([LeadStatus.CONNECTED], "complete")
        self.status = LeadStatus.COMPLETED
        self.outcome = outcome
        self._record_call_attempt(outcome=outcome)
        self._update_timestamp()

    def fail(self, reason: str) -> None:
        """
        Transition to FAILED status with a reason.

        Only allowed from CALLING status.

        Args:
            reason: Why the call failed (e.g., "no_answer", "busy", "machine", "invalid_number")
        """
        self._can_transition_from([LeadStatus.CALLING], "fail")
        self.status = LeadStatus.FAILED
        self.fail_reason = reason
        self._record_call_attempt(reason=reason)
        self._update_timestamp()

    def retry(self) -> None:
        """
        Reset to PENDING status for retry.

        Only allowed from FAILED status and if retry limit not reached.
        """
        self._can_transition_from([LeadStatus.FAILED], "retry")

        if self.retry_count >= self.max_retries:
            raise InvalidStatusTransitionError(self.status, "retry (max retries reached)")

        self.status = LeadStatus.PENDING
        self.retry_count += 1
        self.fail_reason = None
        self._update_timestamp()

    def mark_dnc(self) -> None:
        """
        Mark lead as Do Not Call.

        Can be called from any status except DNC itself.
        Once marked DNC, the lead cannot transition to any other status.
        """
        if self.status == LeadStatus.DNC:
            return  # Already DNC, no-op

        self.status = LeadStatus.DNC
        self._update_timestamp()

    def _record_call_attempt(self, outcome: str | None = None, reason: str | None = None) -> None:
        """Record a call attempt in history."""
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_number": len(self.call_history) + 1,
        }
        if outcome:
            record["outcome"] = outcome
        if reason:
            record["reason"] = reason

        self.call_history.append(record)

    def can_be_called(self) -> bool:
        """Check if this lead can be called."""
        return self.status == LeadStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "notes": self.notes,
            "status": self.status.value,
            "outcome": self.outcome,
            "fail_reason": self.fail_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_called_at": self.last_called_at.isoformat() if self.last_called_at else None,
            "call_history": self.call_history,
            "campaign_id": self.campaign_id,
        }
