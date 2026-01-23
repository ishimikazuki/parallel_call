"""Campaign API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.services.csv_parser import parse_csv
from app.models.campaign import Campaign, InvalidCampaignStateError
from app.models.lead import Lead
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatsResponse,
    LeadCreate,
    LeadResponse,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# In-memory campaign store (replace with DB in production)
CAMPAIGNS_DB: dict[str, Campaign] = {}


def _campaign_to_response(campaign: Campaign) -> CampaignResponse:
    """Convert Campaign model to response schema."""
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        dial_ratio=campaign.dial_ratio,
        caller_id=campaign.caller_id,
        lead_count=len(campaign.leads),
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
    )


def _lead_to_response(lead: Lead) -> LeadResponse:
    """Convert Lead model to response schema."""
    return LeadResponse(
        id=lead.id,
        phone_number=lead.phone_number,
        name=lead.name,
        company=lead.company,
        email=lead.email,
        status=lead.status.value,
        outcome=lead.outcome,
        retry_count=lead.retry_count,
        created_at=lead.created_at,
        last_called_at=lead.last_called_at,
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Create a new campaign."""
    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        dial_ratio=campaign_data.dial_ratio,
        caller_id=campaign_data.caller_id,
    )
    CAMPAIGNS_DB[campaign.id] = campaign
    return _campaign_to_response(campaign)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[CampaignResponse]:
    """List all campaigns."""
    return [_campaign_to_response(c) for c in CAMPAIGNS_DB.values()]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Get campaign by ID."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_response(campaign)


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Start a campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        campaign.start()
    except InvalidCampaignStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Pause a running campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        campaign.pause()
    except InvalidCampaignStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Resume a paused campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        campaign.resume()
    except InvalidCampaignStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignResponse:
    """Stop a campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        campaign.stop()
    except InvalidCampaignStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _campaign_to_response(campaign)


@router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CampaignStatsResponse:
    """Get campaign statistics."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    stats = campaign.get_stats()
    return CampaignStatsResponse(
        total_leads=stats.total_leads,
        pending_leads=stats.pending_leads,
        calling_leads=stats.calling_leads,
        connected_leads=stats.connected_leads,
        completed_leads=stats.completed_leads,
        failed_leads=stats.failed_leads,
        dnc_leads=stats.dnc_leads,
        abandon_rate=stats.abandon_rate,
    )


@router.post(
    "/{campaign_id}/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED
)
async def add_lead(
    campaign_id: str,
    lead_data: LeadCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> LeadResponse:
    """Add a lead to a campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        lead = Lead(
            phone_number=lead_data.phone_number,
            name=lead_data.name,
            company=lead_data.company,
            email=lead_data.email,
            notes=lead_data.notes,
        )
        campaign.add_lead(lead)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidCampaignStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _lead_to_response(lead)


@router.get("/{campaign_id}/leads", response_model=list[LeadResponse])
async def list_leads(
    campaign_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> list[LeadResponse]:
    """List all leads in a campaign."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return [_lead_to_response(lead) for lead in campaign.leads]


class ImportResult(BaseModel):
    """Lead import result."""

    imported_count: int
    skipped_count: int
    errors: list[dict[str, str]]


@router.post("/{campaign_id}/leads/import", response_model=ImportResult)
async def import_leads(
    campaign_id: str,
    file: UploadFile,
    current_user: Annotated[dict, Depends(get_current_user)],
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
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Read file content
    content = await file.read()

    # Parse CSV
    try:
        result = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Import leads
    imported_count = 0
    skipped_count = 0
    errors = list(result.errors)  # Copy parse errors

    for parsed_lead in result.leads:
        try:
            lead = Lead(
                phone_number=parsed_lead.phone_number,
                name=parsed_lead.name,
                company=parsed_lead.company,
                email=parsed_lead.email,
                notes=parsed_lead.notes,
            )
            campaign.add_lead(lead)
            imported_count += 1
        except ValueError as e:
            skipped_count += 1
            errors.append({"phone": parsed_lead.phone_number, "error": str(e)})
        except InvalidCampaignStateError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return ImportResult(
        imported_count=imported_count,
        skipped_count=skipped_count + len(result.errors),
        errors=errors,
    )
