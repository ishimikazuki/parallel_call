"""Unit tests for Operator WebSocket."""

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


class TestOperatorWebSocketConnection:
    """Tests for operator WebSocket connection."""

    def test_connect_with_valid_token(self, client: TestClient, auth_token: str):
        """有効なトークンで接続成功"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            # Should receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"
            assert "user_id" in data["data"]

    def test_connect_without_token_fails(self, client: TestClient):
        """トークンなしで接続失敗"""
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/operator") as websocket:
                websocket.receive_json()

    def test_connect_with_invalid_token_fails(self, client: TestClient):
        """無効なトークンで接続失敗"""
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/operator?token=invalid") as websocket:
                websocket.receive_json()


class TestOperatorStatusChange:
    """Tests for operator status changes via WebSocket."""

    def test_operator_can_go_available(self, client: TestClient, auth_token: str):
        """オペレーターがavailableに変更可能"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            # Receive connected event
            websocket.receive_json()

            # Send status change
            websocket.send_json({
                "action": "set_status",
                "status": "available",
            })

            # Should receive confirmation
            data = websocket.receive_json()
            assert data["event"] == "operator_status_changed"
            assert data["data"]["status"] == "available"

    def test_operator_can_go_on_break(self, client: TestClient, auth_token: str):
        """オペレーターが休憩に変更可能"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            # First go available
            websocket.send_json({"action": "set_status", "status": "available"})
            websocket.receive_json()

            # Then go on break
            websocket.send_json({"action": "set_status", "status": "on_break"})
            data = websocket.receive_json()
            assert data["event"] == "operator_status_changed"
            assert data["data"]["status"] == "on_break"

    def test_operator_can_go_offline(self, client: TestClient, auth_token: str):
        """オペレーターがofflineに変更可能"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "set_status", "status": "offline"})
            data = websocket.receive_json()
            assert data["event"] == "operator_status_changed"
            assert data["data"]["status"] == "offline"


class TestOperatorCallHandling:
    """Tests for call handling via WebSocket."""

    def test_operator_receives_incoming_call(self, client: TestClient, auth_token: str):
        """オペレーターが着信を受信"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            # Go available first
            websocket.send_json({"action": "set_status", "status": "available"})
            websocket.receive_json()  # status changed

            # Simulate incoming call (in real app, this comes from call service)
            # For test, we'll send a test message
            websocket.send_json({
                "action": "test_incoming_call",
                "call_sid": "CA123",
                "lead_id": "lead-001",
                "phone_number": "+818011112222",
                "name": "テスト太郎",
            })

            data = websocket.receive_json()
            assert data["event"] == "incoming_call"
            assert data["data"]["call_sid"] == "CA123"

    def test_operator_can_accept_call(self, client: TestClient, auth_token: str):
        """オペレーターが通話を受ける"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "set_status", "status": "available"})
            websocket.receive_json()

            # Accept a call
            websocket.send_json({
                "action": "accept_call",
                "call_sid": "CA123",
            })

            data = websocket.receive_json()
            assert data["event"] == "call_connected"

    def test_operator_can_end_call(self, client: TestClient, auth_token: str):
        """オペレーターが通話を終了"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "set_status", "status": "available"})
            websocket.receive_json()

            # End a call
            websocket.send_json({
                "action": "end_call",
                "call_sid": "CA123",
                "outcome": "interested",
            })

            data = websocket.receive_json()
            assert data["event"] == "call_ended"
            assert data["data"]["outcome"] == "interested"


class TestOperatorPing:
    """Tests for ping/pong heartbeat."""

    def test_ping_pong(self, client: TestClient, auth_token: str):
        """Ping-Pongハートビート"""
        with client.websocket_connect(f"/ws/operator?token={auth_token}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"action": "ping"})
            data = websocket.receive_json()
            assert data["event"] == "pong"
