"""Campaign API endpoints."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.db.models import CampaignDB, LeadDB
from app.db.session import get_session
from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatsResponse,
    LeadCreate,
    LeadResponse,
)
from app.services.csv_parser import parse_csv

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Legacy in-memory store (kept for backward-compatible tests)
CAMPAIGNS_DB: dict[str, Campaign] = {}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _status_value(status: CampaignStatus | str) -> str:
    if isinstance(status, CampaignStatus):
        return status.value
    return str(status)


def _campaign_to_response(campaign: CampaignDB, lead_count: int) -> CampaignResponse:
    """Convert Campaign DB model to response schema."""
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=_status_value(campaign.status),
        dial_ratio=campaign.dial_ratio,
        caller_id=campaign.caller_id,
        lead_count=lead_count,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
    )


def _lead_to_response(lead: LeadDB) -> LeadResponse:
    """Convert Lead DB model to response schema."""
    status_value = lead.status.value if hasattr(lead.status, "value") else str(lead.status)
    return LeadResponse(
        id=lead.id,
        phone_number=lead.phone_number,
        name=lead.name,
        company=lead.company,
        email=lead.email,
        status=status_value,
        outcome=lead.outcome,
        retry_count=lead.retry_count,
        created_at=lead.created_at,
        last_called_at=lead.last_called_at,
    )


def _raise_transition_error(
    status_value: CampaignStatus,
    action: str,
    reason: str | None = None,
) -> None:
    detail = f"Cannot {action} campaign in {status_value.value} status"
    if reason:
        detail += f": {reason}"
    raise HTTPException(status_code=400, detail=detail)


async def _get_campaign(session: AsyncSession, campaign_id: str) -> CampaignDB | None:
    result = await session.execute(select(CampaignDB).where(CampaignDB.id == campaign_id))
    return result.scalar_one_or_none()


async def _get_campaign_with_lead_count(
    session: AsyncSession, campaign_id: str
) -> tuple[CampaignDB, int] | None:
    stmt = (
        select(CampaignDB, func.count(LeadDB.id))
        .outerjoin(LeadDB, LeadDB.campaign_id == CampaignDB.id)
        .where(CampaignDB.id == campaign_id)
        .group_by(CampaignDB.id)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], int(row[1])


async def _get_lead_count(session: AsyncSession, campaign_id: str) -> int:
    result = await session.execute(
        select(func.count(LeadDB.id)).where(LeadDB.campaign_id == campaign_id)
    )
    return int(result.scalar_one())


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Create a new campaign."""
    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        dial_ratio=campaign_data.dial_ratio,
        caller_id=campaign_data.caller_id,
    )

    campaign_db = CampaignDB(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        dial_ratio=campaign.dial_ratio,
        caller_id=campaign.caller_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )
    session.add(campaign_db)
    await session.commit()
    await session.refresh(campaign_db)

    return _campaign_to_response(campaign_db, lead_count=0)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CampaignResponse]:
    """List all campaigns."""
    stmt = (
        select(CampaignDB, func.count(LeadDB.id))
        .outerjoin(LeadDB, LeadDB.campaign_id == CampaignDB.id)
        .group_by(CampaignDB.id)
    )
    result = await session.execute(stmt)
    return [_campaign_to_response(campaign, int(count)) for campaign, count in result.all()]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Get campaign by ID."""
    row = await _get_campaign_with_lead_count(session, campaign_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign, lead_count = row
    return _campaign_to_response(campaign, lead_count)


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Start a campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.DRAFT:
        _raise_transition_error(campaign.status, "start")

    lead_count = await _get_lead_count(session, campaign_id)
    if lead_count == 0:
        _raise_transition_error(campaign.status, "start", "no leads in campaign")

    now = _utc_now()
    campaign.status = CampaignStatus.RUNNING
    campaign.started_at = now
    campaign.updated_at = now
    await session.commit()
    await session.refresh(campaign)

    return _campaign_to_response(campaign, lead_count=lead_count)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Pause a running campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.RUNNING:
        _raise_transition_error(campaign.status, "pause")

    now = _utc_now()
    campaign.status = CampaignStatus.PAUSED
    campaign.updated_at = now
    await session.commit()
    await session.refresh(campaign)

    lead_count = await _get_lead_count(session, campaign_id)
    return _campaign_to_response(campaign, lead_count=lead_count)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Resume a paused campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.PAUSED:
        _raise_transition_error(campaign.status, "resume")

    now = _utc_now()
    campaign.status = CampaignStatus.RUNNING
    campaign.updated_at = now
    await session.commit()
    await session.refresh(campaign)

    lead_count = await _get_lead_count(session, campaign_id)
    return _campaign_to_response(campaign, lead_count=lead_count)


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    """Stop a campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
        _raise_transition_error(campaign.status, "stop")

    now = _utc_now()
    campaign.status = CampaignStatus.STOPPED
    campaign.updated_at = now
    await session.commit()
    await session.refresh(campaign)

    lead_count = await _get_lead_count(session, campaign_id)
    return _campaign_to_response(campaign, lead_count=lead_count)


@router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignStatsResponse:
    """Get campaign statistics."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    stmt = (
        select(LeadDB.status, func.count(LeadDB.id))
        .where(LeadDB.campaign_id == campaign_id)
        .group_by(LeadDB.status)
    )
    result = await session.execute(stmt)

    pending = calling = connected = completed = failed = dnc = 0
    total = 0

    for status_value, count in result.all():
        count = int(count)
        total += count
        status = status_value if isinstance(status_value, LeadStatus) else LeadStatus(status_value)
        if status == LeadStatus.PENDING:
            pending += count
        elif status == LeadStatus.CALLING:
            calling += count
        elif status == LeadStatus.CONNECTED:
            connected += count
        elif status == LeadStatus.COMPLETED:
            completed += count
        elif status == LeadStatus.FAILED:
            failed += count
        elif status == LeadStatus.DNC:
            dnc += count

    abandon_rate = 0.0

    return CampaignStatsResponse(
        total_leads=total,
        pending_leads=pending,
        calling_leads=calling,
        connected_leads=connected,
        completed_leads=completed,
        failed_leads=failed,
        dnc_leads=dnc,
        abandon_rate=abandon_rate,
    )


@router.post(
    "/{campaign_id}/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED
)
async def add_lead(
    campaign_id: str,
    lead_data: LeadCreate,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadResponse:
    """Add a lead to a campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in [CampaignStatus.STOPPED, CampaignStatus.COMPLETED]:
        _raise_transition_error(campaign.status, "add lead")

    try:
        lead = Lead(
            phone_number=lead_data.phone_number,
            name=lead_data.name,
            company=lead_data.company,
            email=lead_data.email,
            notes=lead_data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing = await session.execute(
        select(LeadDB.id).where(
            LeadDB.campaign_id == campaign_id, LeadDB.phone_number == lead.phone_number
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Phone number {lead.phone_number} already exists in campaign",
        )

    lead_db = LeadDB(
        id=lead.id,
        campaign_id=campaign_id,
        phone_number=lead.phone_number,
        name=lead.name,
        company=lead.company,
        email=lead.email,
        notes=lead.notes,
        status=lead.status,
        outcome=lead.outcome,
        fail_reason=lead.fail_reason,
        retry_count=lead.retry_count,
        max_retries=lead.max_retries,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        last_called_at=lead.last_called_at,
        call_history=lead.call_history,
    )

    now = _utc_now()
    campaign.updated_at = now
    session.add(lead_db)
    await session.commit()
    await session.refresh(lead_db)

    return _lead_to_response(lead_db)


@router.get("/{campaign_id}/leads", response_model=list[LeadResponse])
async def list_leads(
    campaign_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LeadResponse]:
    """List all leads in a campaign."""
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await session.execute(
        select(LeadDB).where(LeadDB.campaign_id == campaign_id).order_by(LeadDB.created_at)
    )
    leads = result.scalars().all()
    return [_lead_to_response(lead) for lead in leads]


class ImportResult(BaseModel):
    """Lead import result."""

    imported_count: int
    skipped_count: int
    errors: list[dict[str, str]]


@router.post("/{campaign_id}/leads/import", response_model=ImportResult)
async def import_leads(
    campaign_id: str,
    file: UploadFile,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImportResult:
    """
    Import leads from CSV file.

    CSV must have a 'phone_number' column. Optional columns:
    - name
    - company
    - email
    - notes

    Supports UTF-8 and Shift_JIS encoding (auto-detected).
    """
    campaign = await _get_campaign(session, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in [CampaignStatus.STOPPED, CampaignStatus.COMPLETED]:
        _raise_transition_error(campaign.status, "add lead")

    content = await file.read()

    try:
        result = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing_numbers = set(
        (
            await session.execute(
                select(LeadDB.phone_number).where(LeadDB.campaign_id == campaign_id)
            )
        )
        .scalars()
        .all()
    )

    imported_count = 0
    skipped_count = 0
    errors = list(result.errors)

    for parsed_lead in result.leads:
        if parsed_lead.phone_number in existing_numbers:
            skipped_count += 1
            errors.append(
                {
                    "phone": parsed_lead.phone_number,
                    "error": f"Phone number {parsed_lead.phone_number} already exists in campaign",
                }
            )
            continue

        try:
            lead = Lead(
                phone_number=parsed_lead.phone_number,
                name=parsed_lead.name,
                company=parsed_lead.company,
                email=parsed_lead.email,
                notes=parsed_lead.notes,
            )
        except ValueError as e:
            skipped_count += 1
            errors.append({"phone": parsed_lead.phone_number, "error": str(e)})
            continue

        lead_db = LeadDB(
            id=lead.id,
            campaign_id=campaign_id,
            phone_number=lead.phone_number,
            name=lead.name,
            company=lead.company,
            email=lead.email,
            notes=lead.notes,
            status=lead.status,
            outcome=lead.outcome,
            fail_reason=lead.fail_reason,
            retry_count=lead.retry_count,
            max_retries=lead.max_retries,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
            last_called_at=lead.last_called_at,
            call_history=lead.call_history,
        )
        session.add(lead_db)
        existing_numbers.add(parsed_lead.phone_number)
        imported_count += 1

    if imported_count > 0:
        campaign.updated_at = _utc_now()

    await session.commit()

    return ImportResult(
        imported_count=imported_count,
        skipped_count=skipped_count + len(result.errors),
        errors=errors,
    )
