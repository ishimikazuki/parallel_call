"""Unit tests for Dashboard WebSocket."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client: TestClient) -> str:
    """Get auth token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    return response.json()["access_token"]


class TestDashboardWebSocketConnection:
    """Tests for dashboard WebSocket connection."""

    def test_connect_with_valid_token(self, client: TestClient, auth_token: str):
        """有効なトークンで接続成功"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            data = websocket.receive_json()
            assert data["event"] == "connected"

    def test_connect_without_token_fails(self, client: TestClient):
        """トークンなしで接続失敗"""
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/dashboard") as websocket:
                websocket.receive_json()


class TestDashboardSubscription:
    """Tests for dashboard subscriptions."""

    def test_subscribe_to_campaign(self, client: TestClient, auth_token: str):
        """キャンペーンにサブスクライブ"""
        # First create a campaign
        response = client.post(
            "/api/v1/campaigns",
            json={"name": "Test Campaign"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        campaign_id = response.json()["id"]

        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({
                "action": "subscribe_campaign",
                "campaign_id": campaign_id,
            })

            data = websocket.receive_json()
            assert data["event"] == "campaign_stats_updated"
            assert data["data"]["campaign_id"] == campaign_id

    def test_get_operators_list(self, client: TestClient, auth_token: str):
        """オペレーター一覧取得"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "get_operators"})

            data = websocket.receive_json()
            assert data["event"] == "operator_list_updated"
            assert "operators" in data["data"]


class TestDashboardAlerts:
    """Tests for dashboard alerts."""

    def test_receive_alert(self, client: TestClient, auth_token: str):
        """アラートを受信"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            # Send test alert
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "long_idle",
                "message": "Operator has been idle for too long",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "long_idle"


class TestDashboardPing:
    """Tests for ping/pong heartbeat."""

    def test_ping_pong(self, client: TestClient, auth_token: str):
        """Ping-Pongハートビート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "ping"})
            data = websocket.receive_json()
            assert data["event"] == "pong"
