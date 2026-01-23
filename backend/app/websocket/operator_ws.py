"""Operator WebSocket handler."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.auth_service import verify_access_token, get_user
from app.services.operator_manager import OperatorSession, OperatorStatus
from app.websocket.connection_manager import (
    manager,
    EventType,
    WebSocketMessage,
)

router = APIRouter()

# In-memory operator sessions (shared with operator_manager)
operator_sessions: dict[str, OperatorSession] = {}


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


async def handle_operator_message(
    user_id: str,
    message: dict[str, Any],
    websocket: WebSocket,
) -> WebSocketMessage | None:
    """
    Handle incoming message from operator.

    Returns a message to send back, or None.
    """
    action = message.get("action")

    if action == "ping":
        return WebSocketMessage(event=EventType.PING, data={})

    elif action == "set_status":
        new_status = message.get("status")
        session = operator_sessions.get(user_id)

        if not session:
            # Create new session
            session = OperatorSession(id=user_id, name=user_id)
            operator_sessions[user_id] = session

        # Update status
        if new_status == "available":
            session.go_online()
        elif new_status == "on_break":
            session.go_on_break()
        elif new_status == "offline":
            session.go_offline()
        elif new_status == "wrap_up":
            session.start_wrap_up()

        # Broadcast to dashboards
        await manager.broadcast_to_dashboards(
            WebSocketMessage(
                event=EventType.OPERATOR_LIST_UPDATED,
                data={
                    "operator_id": user_id,
                    "status": session.status.value,
                },
            )
        )

        return WebSocketMessage(
            event=EventType.OPERATOR_STATUS_CHANGED,
            data={
                "operator_id": user_id,
                "status": session.status.value,
            },
        )

    elif action == "test_incoming_call":
        # For testing - simulate an incoming call
        return WebSocketMessage(
            event=EventType.INCOMING_CALL,
            data={
                "call_sid": message.get("call_sid"),
                "lead_id": message.get("lead_id"),
                "phone_number": message.get("phone_number"),
                "name": message.get("name"),
            },
        )

    elif action == "accept_call":
        call_sid = message.get("call_sid")
        session = operator_sessions.get(user_id)

        if session:
            session.start_call(call_sid=call_sid, lead_id=message.get("lead_id", ""))

        # Broadcast to dashboards
        await manager.broadcast_to_dashboards(
            WebSocketMessage(
                event=EventType.OPERATOR_LIST_UPDATED,
                data={
                    "operator_id": user_id,
                    "status": "on_call",
                    "call_sid": call_sid,
                },
            )
        )

        return WebSocketMessage(
            event=EventType.CALL_CONNECTED,
            data={
                "call_sid": call_sid,
                "operator_id": user_id,
            },
        )

    elif action == "end_call":
        call_sid = message.get("call_sid")
        outcome = message.get("outcome")
        session = operator_sessions.get(user_id)

        if session:
            session.end_call()

        # Broadcast to dashboards
        await manager.broadcast_to_dashboards(
            WebSocketMessage(
                event=EventType.OPERATOR_LIST_UPDATED,
                data={
                    "operator_id": user_id,
                    "status": "available",
                },
            )
        )

        return WebSocketMessage(
            event=EventType.CALL_ENDED,
            data={
                "call_sid": call_sid,
                "operator_id": user_id,
                "outcome": outcome,
            },
        )

    return None


@router.websocket("/ws/operator")
async def operator_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    WebSocket endpoint for operators.

    Handles:
    - Status changes (available, on_break, offline)
    - Incoming call notifications
    - Call accept/end actions

    Query params:
        token: JWT access token for authentication
    """
    # Authenticate
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = user["id"]

    # Connect
    try:
        await manager.connect(
            websocket=websocket,
            user_id=user_id,
            connection_type="operator",
            metadata={"username": user["username"], "role": user["role"]},
        )

        # Create operator session if not exists
        if user_id not in operator_sessions:
            operator_sessions[user_id] = OperatorSession(
                id=user_id,
                name=user["username"],
            )

        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                response = await handle_operator_message(user_id, message, websocket)
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
        # Mark operator as offline
        session = operator_sessions.get(user_id)
        if session:
            session.go_offline()
