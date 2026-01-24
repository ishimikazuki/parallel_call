"""Dashboard WebSocket handler."""

import json
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CampaignDB, LeadDB
from app.db.session import get_session
from app.models.lead import LeadStatus
from app.services.auth_service import get_user, verify_access_token
from app.websocket.connection_manager import (
    EventType,
    WebSocketMessage,
    manager,
)
from app.websocket.operator_ws import operator_sessions

router = APIRouter()


async def authenticate_websocket(token: str | None) -> dict[str, Any] | None:
    """Authenticate WebSocket connection using JWT token."""
    if not token:
        return None

    payload = verify_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    return get_user(username)


async def get_campaign_stats(
    session: AsyncSession,
    campaign_id: str,
) -> dict[str, Any] | None:
    """Get campaign statistics."""
    campaign = await session.get(CampaignDB, campaign_id)
    if not campaign:
        return None

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

    return {
        "campaign_id": campaign_id,
        "name": campaign.name,
        "status": campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
        "total_leads": total,
        "pending_leads": pending,
        "calling_leads": calling,
        "connected_leads": connected,
        "completed_leads": completed,
        "failed_leads": failed,
        "dnc_leads": dnc,
        "abandon_rate": abandon_rate,
    }


def get_operators_list() -> list[dict[str, Any]]:
    """Get list of all operators and their statuses."""
    operators = []
    for op_id, session in operator_sessions.items():
        operators.append({
            "id": op_id,
            "name": session.name,
            "status": session.status.value,
            "current_call_sid": session.current_call_sid,
            "idle_duration_seconds": session.idle_duration_seconds,
            "calls_handled": session.calls_handled,
        })
    return operators


async def handle_dashboard_message(
    user_id: str,
    message: dict[str, Any],
    websocket: WebSocket,
    session: AsyncSession,
) -> WebSocketMessage | None:
    """
    Handle incoming message from dashboard.

    Returns a message to send back, or None.
    """
    action = message.get("action")

    if action == "ping":
        return WebSocketMessage(event=EventType.PING, data={})

    elif action == "subscribe_campaign":
        campaign_id = message.get("campaign_id")
        if not isinstance(campaign_id, str):
            return WebSocketMessage(
                event=EventType.ERROR,
                data={"message": "campaign_id is required"},
            )

        stats = await get_campaign_stats(session, campaign_id)

        if stats:
            return WebSocketMessage(
                event=EventType.CAMPAIGN_STATS_UPDATED,
                data=stats,
            )
        else:
            return WebSocketMessage(
                event=EventType.ERROR,
                data={"message": f"Campaign {campaign_id} not found"},
            )

    elif action == "get_operators":
        operators = get_operators_list()
        return WebSocketMessage(
            event=EventType.OPERATOR_LIST_UPDATED,
            data={"operators": operators},
        )

    elif action == "test_alert":
        # For testing - simulate an alert
        return WebSocketMessage(
            event=EventType.ALERT,
            data={
                "alert_type": message.get("alert_type"),
                "message": message.get("message"),
                "severity": message.get("severity", "warning"),
            },
        )

    elif action == "refresh_stats":
        campaign_id = message.get("campaign_id")
        if isinstance(campaign_id, str):
            stats = await get_campaign_stats(session, campaign_id)
            if stats:
                return WebSocketMessage(
                    event=EventType.CAMPAIGN_STATS_UPDATED,
                    data=stats,
                )

    return None


@router.websocket("/ws/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    session: Annotated[AsyncSession, Depends(get_session)],
    token: str | None = Query(None),
) -> None:
    """
    WebSocket endpoint for dashboard.

    Handles:
    - Campaign subscription and stats updates
    - Operator list updates
    - Alerts

    Query params:
        token: JWT access token for authentication
    """
    # Authenticate
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = f"dashboard-{user['id']}"

    # Connect
    try:
        await manager.connect(
            websocket=websocket,
            user_id=user_id,
            connection_type="dashboard",
            metadata={"username": user["username"], "role": user["role"]},
        )

        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                response = await handle_dashboard_message(user_id, message, websocket, session)
                if response:
                    # Handle ping specially
                    if response.event == EventType.PING:
                        await websocket.send_text(
                            WebSocketMessage(event=EventType.PONG, data={}).to_json()
                        )
                    else:
                        await websocket.send_text(response.to_json())

            except json.JSONDecodeError:
                await websocket.send_text(
                    WebSocketMessage(
                        event=EventType.ERROR,
                        data={"message": "Invalid JSON"},
                    ).to_json()
                )

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id)
