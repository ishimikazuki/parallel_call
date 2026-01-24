"""SQLAlchemy ORM models."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.campaign import CampaignStatus
from app.models.lead import LeadStatus


def utc_now() -> datetime:
    """Timezone-aware UTC now for defaults."""
    return datetime.now(UTC)


class CampaignDB(Base):
    """Campaign table."""

    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        default=CampaignStatus.DRAFT,
        nullable=False,
    )
    dial_ratio: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    caller_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    leads: Mapped[list["LeadDB"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class LeadDB(Base):
    """Lead table."""

    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("campaign_id", "phone_number", name="uq_leads_campaign_phone"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    company: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"),
        default=LeadStatus.PENDING,
        nullable=False,
    )
    outcome: Mapped[str | None] = mapped_column(String(100))
    fail_reason: Mapped[str | None] = mapped_column(String(100))

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    call_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    campaign: Mapped[CampaignDB] = relationship(back_populates="leads")
