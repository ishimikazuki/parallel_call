"""Dashboard WebSocket handler."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.auth_service import verify_access_token, get_user
from app.api.v1.campaigns import CAMPAIGNS_DB
from app.websocket.operator_ws import operator_sessions
from app.websocket.connection_manager import (
    manager,
    EventType,
    WebSocketMessage,
)

router = APIRouter()


async def authenticate_websocket(token: str | None) -> dict | None:
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


def get_campaign_stats(campaign_id: str) -> dict[str, Any] | None:
    """Get campaign statistics."""
    campaign = CAMPAIGNS_DB.get(campaign_id)
    if not campaign:
        return None

    stats = campaign.get_stats()
    return {
        "campaign_id": campaign_id,
        "name": campaign.name,
        "status": campaign.status.value,
        "total_leads": stats.total_leads,
        "pending_leads": stats.pending_leads,
        "calling_leads": stats.calling_leads,
        "connected_leads": stats.connected_leads,
        "completed_leads": stats.completed_leads,
        "failed_leads": stats.failed_leads,
        "abandon_rate": stats.abandon_rate,
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
        stats = get_campaign_stats(campaign_id)

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
        if campaign_id:
            stats = get_campaign_stats(campaign_id)
            if stats:
                return WebSocketMessage(
                    event=EventType.CAMPAIGN_STATS_UPDATED,
                    data=stats,
                )

    return None


@router.websocket("/ws/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):
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

                response = await handle_dashboard_message(user_id, message, websocket)
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
