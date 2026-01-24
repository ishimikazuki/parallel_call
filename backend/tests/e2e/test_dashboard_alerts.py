"""E2E Test: Dashboard Alerts

Tests the alert system:
1. Long idle operator detection
2. High abandon rate alert
3. Campaign completion alert
4. System error alerts
"""

from datetime import UTC, datetime, timedelta

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.campaign import CampaignStats
from app.services.operator_manager import OperatorManager, OperatorSession, OperatorStatus


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


class TestLongIdleOperatorAlert:
    """Tests for long idle operator detection."""

    def test_detect_long_idle_operator(self):
        """長時間離席オペレーターの検出"""
        manager = OperatorManager()

        # Add operator who has been idle for a long time
        op1 = OperatorSession(id="op1", name="Long Idle Op")
        op1.status = OperatorStatus.AVAILABLE
        # Simulate 10 minutes idle
        op1._idle_since = datetime.now(UTC) - timedelta(minutes=10)
        manager.add_operator(op1)

        # Check idle duration
        idle_threshold_seconds = 300  # 5 minutes
        assert op1.idle_duration_seconds > idle_threshold_seconds

    def test_long_idle_operator_list(self):
        """長時間離席オペレーターのリスト取得"""
        manager = OperatorManager()

        # Add multiple operators
        op1 = OperatorSession(id="op1", name="Short Idle")
        op1.status = OperatorStatus.AVAILABLE
        op1._idle_since = datetime.now(UTC) - timedelta(minutes=2)

        op2 = OperatorSession(id="op2", name="Long Idle")
        op2.status = OperatorStatus.AVAILABLE
        op2._idle_since = datetime.now(UTC) - timedelta(minutes=10)

        op3 = OperatorSession(id="op3", name="On Call")
        op3.status = OperatorStatus.ON_CALL

        manager.add_operator(op1)
        manager.add_operator(op2)
        manager.add_operator(op3)

        # Find operators idle for more than 5 minutes using get_long_idle_operators
        long_idle_operators = manager.get_long_idle_operators()

        assert len(long_idle_operators) == 1
        assert long_idle_operators[0].id == "op2"

    def test_websocket_alert_for_long_idle(
        self, client: TestClient, auth_token: str
    ):
        """WebSocket経由の長時間離席アラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Simulate sending test alert for long idle
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "long_idle",
                "message": "オペレーター山田が10分以上離席しています",
                "severity": "warning",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "long_idle"
            assert data["data"]["severity"] == "warning"


class TestHighAbandonRateAlert:
    """Tests for high abandon rate alerts."""

    def test_abandon_rate_exceeds_threshold(self):
        """放棄率が閾値を超える"""
        # abandon_rate = 6 / (44 + 6) = 6/50 = 0.12 = 12%
        stats = CampaignStats(
            total_leads=100,
            pending_leads=30,
            calling_leads=10,
            connected_leads=44,
            completed_leads=0,
            failed_leads=10,
            abandoned_leads=6,
        )

        threshold = 0.05  # 5%
        is_high = stats.abandon_rate > threshold
        assert is_high is True

    def test_abandon_rate_alert_via_websocket(
        self, client: TestClient, auth_token: str
    ):
        """WebSocket経由の放棄率アラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Simulate high abandon rate alert
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "high_abandon_rate",
                "message": "放棄率が8%に達しました（目標: 3%以下）",
                "severity": "error",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "high_abandon_rate"
            assert data["data"]["severity"] == "error"


class TestCampaignCompletionAlert:
    """Tests for campaign completion alerts."""

    def test_campaign_completion_detection(self):
        """キャンペーン完了の検出"""
        stats = CampaignStats(
            total_leads=100,
            pending_leads=0,  # No more pending
            calling_leads=0,  # No active calls
            connected_leads=0,
            completed_leads=85,
            failed_leads=10,
            abandoned_leads=5,
        )

        # Check if campaign is complete
        is_complete = (
            stats.pending_leads == 0
            and stats.calling_leads == 0
            and stats.connected_leads == 0
        )
        assert is_complete is True

    def test_campaign_completion_alert_via_websocket(
        self, client: TestClient, auth_token: str
    ):
        """WebSocket経由のキャンペーン完了アラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Simulate campaign completion alert
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "campaign_completed",
                "message": "キャンペーン「テストキャンペーン」が完了しました",
                "severity": "info",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "campaign_completed"
            assert data["data"]["severity"] == "info"


class TestSystemErrorAlert:
    """Tests for system error alerts."""

    def test_twilio_error_alert(self, client: TestClient, auth_token: str):
        """Twilioエラーアラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Simulate Twilio error alert
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "twilio_error",
                "message": "Twilio API接続エラーが発生しました",
                "severity": "error",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "twilio_error"
            assert data["data"]["severity"] == "error"

    def test_database_error_alert(self, client: TestClient, auth_token: str):
        """データベースエラーアラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Simulate database error alert
            websocket.send_json({
                "action": "test_alert",
                "alert_type": "database_error",
                "message": "データベース接続エラー",
                "severity": "error",
            })

            data = websocket.receive_json()
            assert data["event"] == "alert"
            assert data["data"]["alert_type"] == "database_error"


class TestOperatorListUpdates:
    """Tests for real-time operator list updates."""

    def test_get_operators_list(self, client: TestClient, auth_token: str):
        """オペレーターリストの取得"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Request operators list
            websocket.send_json({"action": "get_operators"})

            data = websocket.receive_json()
            assert data["event"] == "operator_list_updated"
            assert "operators" in data["data"]

    def test_ping_pong_heartbeat(self, client: TestClient, auth_token: str):
        """Ping-Pongハートビート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            # Receive connected event
            data = websocket.receive_json()
            assert data["event"] == "connected"

            # Send ping
            websocket.send_json({"action": "ping"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["event"] == "pong"


class TestMultipleAlertsSeverityLevels:
    """Tests for alert severity levels."""

    def test_info_severity_alert(self, client: TestClient, auth_token: str):
        """Info レベルのアラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            data = websocket.receive_json()  # connected

            websocket.send_json({
                "action": "test_alert",
                "alert_type": "info",
                "message": "新しいオペレーターがログインしました",
                "severity": "info",
            })

            data = websocket.receive_json()
            assert data["data"]["severity"] == "info"

    def test_warning_severity_alert(self, client: TestClient, auth_token: str):
        """Warning レベルのアラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            data = websocket.receive_json()  # connected

            websocket.send_json({
                "action": "test_alert",
                "alert_type": "warning",
                "message": "放棄率が目標を超えています",
                "severity": "warning",
            })

            data = websocket.receive_json()
            assert data["data"]["severity"] == "warning"

    def test_error_severity_alert(self, client: TestClient, auth_token: str):
        """Error レベルのアラート"""
        with client.websocket_connect(f"/ws/dashboard?token={auth_token}") as websocket:
            data = websocket.receive_json()  # connected

            websocket.send_json({
                "action": "test_alert",
                "alert_type": "error",
                "message": "システムエラーが発生しました",
                "severity": "error",
            })

            data = websocket.receive_json()
            assert data["data"]["severity"] == "error"
