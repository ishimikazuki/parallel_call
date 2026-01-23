"""WebSocket connection manager."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import WebSocket


class EventType(str, Enum):
    """WebSocket event types."""

    # Operator events
    INCOMING_CALL = "incoming_call"
    CALL_CONNECTED = "call_connected"
    CALL_ENDED = "call_ended"
    OPERATOR_STATUS_CHANGED = "operator_status_changed"

    # Dashboard events
    CAMPAIGN_STATS_UPDATED = "campaign_stats_updated"
    OPERATOR_LIST_UPDATED = "operator_list_updated"
    ALERT = "alert"

    # System events
    CONNECTED = "connected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""

    event: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            {
                "event": self.event.value,
                "data": self.data,
                "timestamp": self.timestamp.isoformat(),
            }
        )


@dataclass
class Connection:
    """WebSocket connection wrapper."""

    websocket: WebSocket
    user_id: str
    connection_type: str  # "operator" or "dashboard"
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class ConnectionManager:
    """
    Manages WebSocket connections.

    Handles:
    - Connection lifecycle (connect, disconnect)
    - Broadcasting messages to specific groups
    - Direct messaging to specific users
    """

    def __init__(self):
        # All active connections
        self._connections: dict[str, Connection] = {}

        # Grouped connections
        self._operator_connections: dict[str, Connection] = {}
        self._dashboard_connections: dict[str, Connection] = {}

    @property
    def operator_count(self) -> int:
        """Number of connected operators."""
        return len(self._operator_connections)

    @property
    def dashboard_count(self) -> int:
        """Number of connected dashboards."""
        return len(self._dashboard_connections)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Connection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket instance
            user_id: Unique identifier for the user
            connection_type: "operator" or "dashboard"
            metadata: Additional connection metadata

        Returns:
            Connection object
        """
        await websocket.accept()

        connection = Connection(
            websocket=websocket,
            user_id=user_id,
            connection_type=connection_type,
            metadata=metadata or {},
        )

        # Store connection
        self._connections[user_id] = connection

        if connection_type == "operator":
            self._operator_connections[user_id] = connection
        elif connection_type == "dashboard":
            self._dashboard_connections[user_id] = connection

        # Send connected confirmation
        await self.send_to_user(
            user_id,
            WebSocketMessage(
                event=EventType.CONNECTED,
                data={"user_id": user_id, "connection_type": connection_type},
            ),
        )

        return connection

    async def disconnect(self, user_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            user_id: The user to disconnect
        """
        connection = self._connections.pop(user_id, None)
        if connection:
            self._operator_connections.pop(user_id, None)
            self._dashboard_connections.pop(user_id, None)

            try:
                await connection.websocket.close()
            except Exception:
                pass  # Connection might already be closed

    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> bool:
        """
        Send a message to a specific user.

        Args:
            user_id: Target user ID
            message: Message to send

        Returns:
            True if sent successfully
        """
        connection = self._connections.get(user_id)
        if not connection:
            return False

        try:
            await connection.websocket.send_text(message.to_json())
            return True
        except Exception:
            # Connection is broken, remove it
            await self.disconnect(user_id)
            return False

    async def broadcast_to_operators(self, message: WebSocketMessage) -> int:
        """
        Broadcast a message to all connected operators.

        Returns:
            Number of operators that received the message
        """
        sent_count = 0
        failed_users = []

        for user_id, connection in self._operator_connections.items():
            try:
                await connection.websocket.send_text(message.to_json())
                sent_count += 1
            except Exception:
                failed_users.append(user_id)

        # Clean up failed connections
        for user_id in failed_users:
            await self.disconnect(user_id)

        return sent_count

    async def broadcast_to_dashboards(self, message: WebSocketMessage) -> int:
        """
        Broadcast a message to all connected dashboards.

        Returns:
            Number of dashboards that received the message
        """
        sent_count = 0
        failed_users = []

        for user_id, connection in self._dashboard_connections.items():
            try:
                await connection.websocket.send_text(message.to_json())
                sent_count += 1
            except Exception:
                failed_users.append(user_id)

        # Clean up failed connections
        for user_id in failed_users:
            await self.disconnect(user_id)

        return sent_count

    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """
        Broadcast a message to all connected clients.

        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        failed_users = []

        for user_id, connection in self._connections.items():
            try:
                await connection.websocket.send_text(message.to_json())
                sent_count += 1
            except Exception:
                failed_users.append(user_id)

        # Clean up failed connections
        for user_id in failed_users:
            await self.disconnect(user_id)

        return sent_count

    def get_connection(self, user_id: str) -> Connection | None:
        """Get a connection by user ID."""
        return self._connections.get(user_id)

    def get_all_operator_ids(self) -> list[str]:
        """Get all connected operator user IDs."""
        return list(self._operator_connections.keys())

    def get_all_dashboard_ids(self) -> list[str]:
        """Get all connected dashboard user IDs."""
        return list(self._dashboard_connections.keys())


# Global connection manager instance
manager = ConnectionManager()
