"""Campaign domain model."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.models.lead import Lead, LeadStatus


class CampaignStatus(str, Enum):
    """Campaign status."""

    DRAFT = "draft"  # 作成中、未開始
    RUNNING = "running"  # 実行中
    PAUSED = "paused"  # 一時停止中
    STOPPED = "stopped"  # 停止（再開不可）
    COMPLETED = "completed"  # 完了


class InvalidCampaignStateError(Exception):
    """Raised when an invalid campaign state transition is attempted."""

    def __init__(self, current_status: CampaignStatus, attempted_action: str, reason: str = ""):
        self.current_status = current_status
        self.attempted_action = attempted_action
        self.reason = reason
        message = f"Cannot {attempted_action} campaign in {current_status.value} status"
        if reason:
            message += f": {reason}"
        super().__init__(message)


@dataclass
class CampaignStats:
    """Campaign statistics."""

    total_leads: int = 0
    pending_leads: int = 0
    calling_leads: int = 0
    connected_leads: int = 0
    completed_leads: int = 0
    failed_leads: int = 0
    dnc_leads: int = 0
    abandoned_leads: int = 0  # オペレーター接続前に切られた数

    @property
    def abandon_rate(self) -> float:
        """
        Calculate abandon rate.

        Abandon rate = abandoned / (connected + abandoned)
        """
        total_answered = self.connected_leads + self.abandoned_leads
        if total_answered == 0:
            return 0.0
        return self.abandoned_leads / total_answered


@dataclass
class Campaign:
    """
    Campaign (キャンペーン) domain model.

    Represents a calling campaign with a list of leads to call.
    """

    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""

    # Status
    status: CampaignStatus = CampaignStatus.DRAFT

    # Dialer settings
    dial_ratio: float = 3.0  # 同時発信数 / 待機オペレーター数
    caller_id: str | None = None  # 発信元電話番号

    # Leads
    leads: list[Lead] = field(default_factory=list)
    _phone_numbers: set[str] = field(default_factory=set)  # 重複チェック用

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate campaign on creation."""
        if not self.name or not self.name.strip():
            raise ValueError("Campaign name is required")

        if self.dial_ratio <= 0:
            raise ValueError("Dial ratio must be positive")

    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def add_lead(self, lead: Lead) -> None:
        """
        Add a lead to the campaign.

        Args:
            lead: Lead to add

        Raises:
            ValueError: If phone number already exists in campaign
            InvalidCampaignStateError: If campaign is stopped or completed
        """
        if self.status in [CampaignStatus.STOPPED, CampaignStatus.COMPLETED]:
            raise InvalidCampaignStateError(self.status, "add lead")

        if lead.phone_number in self._phone_numbers:
            raise ValueError(f"Phone number {lead.phone_number} already exists in campaign")

        lead.campaign_id = self.id
        self.leads.append(lead)
        self._phone_numbers.add(lead.phone_number)
        self._update_timestamp()

    def remove_lead(self, lead_id: str) -> Lead | None:
        """
        Remove a lead from the campaign.

        Only allowed for PENDING leads.
        """
        for i, lead in enumerate(self.leads):
            if lead.id == lead_id:
                if lead.status != LeadStatus.PENDING:
                    raise InvalidCampaignStateError(
                        self.status, "remove lead", "can only remove pending leads"
                    )
                removed = self.leads.pop(i)
                self._phone_numbers.discard(removed.phone_number)
                self._update_timestamp()
                return removed
        return None

    def get_next_lead(self) -> Lead | None:
        """
        Get the next lead to call.

        Returns the first PENDING lead, or None if no pending leads.
        """
        if self.status != CampaignStatus.RUNNING:
            return None

        for lead in self.leads:
            if lead.status == LeadStatus.PENDING:
                return lead
        return None

    def get_callable_leads(self, count: int) -> list[Lead]:
        """
        Get multiple callable leads.

        Args:
            count: Maximum number of leads to return

        Returns:
            List of PENDING leads, up to count
        """
        if self.status != CampaignStatus.RUNNING:
            return []

        callable_leads = []
        for lead in self.leads:
            if lead.status == LeadStatus.PENDING:
                callable_leads.append(lead)
                if len(callable_leads) >= count:
                    break
        return callable_leads

    def start(self) -> None:
        """
        Start the campaign.

        Transitions from DRAFT to RUNNING.
        """
        if self.status != CampaignStatus.DRAFT:
            raise InvalidCampaignStateError(self.status, "start")

        if not self.leads:
            raise InvalidCampaignStateError(self.status, "start", "no leads in campaign")

        self.status = CampaignStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self._update_timestamp()

    def pause(self) -> None:
        """
        Pause the campaign.

        Transitions from RUNNING to PAUSED.
        """
        if self.status != CampaignStatus.RUNNING:
            raise InvalidCampaignStateError(self.status, "pause")

        self.status = CampaignStatus.PAUSED
        self._update_timestamp()

    def resume(self) -> None:
        """
        Resume a paused campaign.

        Transitions from PAUSED to RUNNING.
        """
        if self.status != CampaignStatus.PAUSED:
            raise InvalidCampaignStateError(self.status, "resume")

        self.status = CampaignStatus.RUNNING
        self._update_timestamp()

    def stop(self) -> None:
        """
        Stop the campaign.

        Can be called from RUNNING or PAUSED. Cannot be resumed.
        """
        if self.status not in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
            raise InvalidCampaignStateError(self.status, "stop")

        self.status = CampaignStatus.STOPPED
        self._update_timestamp()

    def check_completion(self) -> bool:
        """
        Check if campaign should be marked as completed.

        Returns True if status changed to COMPLETED.
        """
        if self.status != CampaignStatus.RUNNING:
            return False

        # Check if all leads are in terminal states
        for lead in self.leads:
            if lead.status in [LeadStatus.PENDING, LeadStatus.CALLING, LeadStatus.CONNECTED]:
                return False

        self.status = CampaignStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self._update_timestamp()
        return True

    def update_dial_ratio(self, new_ratio: float) -> None:
        """
        Update the dial ratio.

        Args:
            new_ratio: New dial ratio (must be positive)
        """
        if new_ratio <= 0:
            raise ValueError("Dial ratio must be positive")

        self.dial_ratio = new_ratio
        self._update_timestamp()

    def get_stats(self) -> CampaignStats:
        """Calculate current campaign statistics."""
        stats = CampaignStats(total_leads=len(self.leads))

        for lead in self.leads:
            match lead.status:
                case LeadStatus.PENDING:
                    stats.pending_leads += 1
                case LeadStatus.CALLING:
                    stats.calling_leads += 1
                case LeadStatus.CONNECTED:
                    stats.connected_leads += 1
                case LeadStatus.COMPLETED:
                    stats.completed_leads += 1
                case LeadStatus.FAILED:
                    stats.failed_leads += 1
                case LeadStatus.DNC:
                    stats.dnc_leads += 1

        return stats

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "dial_ratio": self.dial_ratio,
            "caller_id": self.caller_id,
            "lead_count": len(self.leads),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stats": {
                "total": self.get_stats().total_leads,
                "pending": self.get_stats().pending_leads,
                "completed": self.get_stats().completed_leads,
                "failed": self.get_stats().failed_leads,
            },
        }
