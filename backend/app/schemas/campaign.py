"""Campaign schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CampaignCreate(BaseModel):
    """Campaign creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    dial_ratio: float = Field(default=3.0, gt=0, le=10)
    caller_id: str | None = None


class CampaignResponse(BaseModel):
    """Campaign response."""

    id: str
    name: str
    description: str
    status: str
    dial_ratio: float
    caller_id: str | None
    lead_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CampaignStatsResponse(BaseModel):
    """Campaign statistics response."""

    total_leads: int
    pending_leads: int
    calling_leads: int
    connected_leads: int
    completed_leads: int
    failed_leads: int
    dnc_leads: int
    abandon_rate: float


class LeadCreate(BaseModel):
    """Lead creation request."""

    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")
    name: str | None = None
    company: str | None = None
    email: str | None = None
    notes: str | None = None


class LeadResponse(BaseModel):
    """Lead response."""

    id: str
    phone_number: str
    name: str | None
    company: str | None
    email: str | None
    status: str
    outcome: str | None
    retry_count: int
    created_at: datetime
    last_called_at: datetime | None
