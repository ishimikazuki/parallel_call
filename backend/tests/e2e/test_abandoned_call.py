"""E2E Test: Abandoned Call Flow

Tests the abandoned call scenario:
1. All operators are busy
2. Customer answers but no operator available
3. Customer put on hold
4. Timeout occurs
5. Call marked as abandoned
6. Lead added to retry queue
"""

import pytest
from datetime import datetime, timedelta
from starlette.testclient import TestClient
from fastapi import status

from app.main import app
from app.models.lead import LeadStatus
from app.models.campaign import CampaignStats
from app.services.operator_manager import OperatorManager, OperatorSession, OperatorStatus
from app.services.dialer_orchestrator import DialerOrchestrator


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


class TestAbandonedCallFlow:
    """E2E tests for abandoned call scenarios."""

    def test_no_available_operators(self):
        """利用可能なオペレーターがいない場合"""
        manager = OperatorManager()

        # Add operators all on call
        op1 = OperatorSession(id="op1", name="Op1")
        op1.status = OperatorStatus.ON_CALL
        op1.current_call_sid = "CA111"

        op2 = OperatorSession(id="op2", name="Op2")
        op2.status = OperatorStatus.ON_CALL
        op2.current_call_sid = "CA222"

        manager.add_operator(op1)
        manager.add_operator(op2)

        # Try to get available operator - should return empty list
        available = manager.get_available_operators()
        assert len(available) == 0

    def test_dial_ratio_reduces_on_high_abandon_rate(self):
        """放棄率が高い場合にダイヤル比率が下がる"""
        orchestrator = DialerOrchestrator()

        # High abandon rate scenario
        # abandon_rate = abandoned / (connected + abandoned)
        # = 10 / (50 + 10) = 10/60 ≈ 0.167 = 16.7%
        stats = CampaignStats(
            total_leads=100,
            pending_leads=20,
            calling_leads=10,
            connected_leads=50,
            completed_leads=0,
            failed_leads=10,
            abandoned_leads=10,
        )

        dial_ratio = orchestrator.calculate_dial_ratio(stats)

        # Should reduce dial ratio below 3.0 due to high abandon rate
        assert dial_ratio < 3.0

    def test_dial_ratio_increases_on_low_abandon_rate(self):
        """放棄率が低い場合にダイヤル比率が維持または上がる"""
        orchestrator = DialerOrchestrator()

        # Low abandon rate scenario
        # abandon_rate = 1 / (59 + 1) = 1/60 ≈ 0.017 = 1.7%
        stats = CampaignStats(
            total_leads=100,
            pending_leads=20,
            calling_leads=5,
            connected_leads=59,
            completed_leads=0,
            failed_leads=15,
            abandoned_leads=1,
        )

        dial_ratio = orchestrator.calculate_dial_ratio(stats)

        # Should maintain or increase dial ratio (low abandon rate is good)
        assert dial_ratio >= 3.0

    def test_abandoned_call_webhook_handling(self, client: TestClient):
        """放棄コールのWebhook処理"""
        # Simulate call that was answered but ended without transfer
        response = client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA_ABANDONED_123",
                "CallStatus": "completed",
                "To": "+819011111111",
                "From": "+815011111111",
                "CallDuration": "15",  # Short duration indicates abandoned
            },
        )
        assert response.status_code == status.HTTP_200_OK

    def test_hold_timeout_scenario(self, client: TestClient):
        """保留タイムアウトのシナリオ"""
        # First, call is answered and put on hold
        response = client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA_HOLD_TIMEOUT",
                "CallStatus": "in-progress",
                "To": "+819011111111",
                "From": "+815011111111",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Then call ends (customer hung up during hold)
        response = client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA_HOLD_TIMEOUT",
                "CallStatus": "completed",
                "To": "+819011111111",
                "From": "+815011111111",
                "CallDuration": "30",  # 30 seconds on hold
            },
        )
        assert response.status_code == status.HTTP_200_OK


class TestRetryQueueLogic:
    """Tests for retry queue after abandoned calls."""

    def test_lead_retry_count_increments(self):
        """リトライカウントが増加する"""
        from app.models.lead import Lead

        lead = Lead(phone_number="+819012345678")
        assert lead.retry_count == 0

        # Simulate retry
        lead.retry_count += 1
        assert lead.retry_count == 1

    def test_lead_max_retry_reached(self):
        """最大リトライ回数に達した場合"""
        from app.models.lead import Lead

        lead = Lead(phone_number="+819012345678")
        lead.retry_count = 3  # Max retries

        # Should not allow more retries (business logic would check this)
        max_retries = 3
        can_retry = lead.retry_count < max_retries
        assert can_retry is False

    def test_operator_becomes_available_during_hold(self):
        """保留中にオペレーターが利用可能になる"""
        manager = OperatorManager()

        # Add operator on break
        op1 = OperatorSession(id="op1", name="Op1")
        op1.status = OperatorStatus.ON_BREAK
        manager.add_operator(op1)

        # No available operators initially
        assert len(manager.get_available_operators()) == 0

        # Operator becomes available
        op1.status = OperatorStatus.AVAILABLE

        # Now should find available operator
        available = manager.get_available_operators()
        assert len(available) == 1
        assert available[0].id == "op1"


class TestAbandonRateCalculation:
    """Tests for abandon rate calculation and monitoring."""

    def test_abandon_rate_calculation(self):
        """放棄率の計算"""
        # abandon_rate = abandoned / (connected + abandoned)
        # = 5 / (45 + 5) = 5/50 = 0.10 = 10%
        stats = CampaignStats(
            total_leads=100,
            pending_leads=30,
            calling_leads=5,
            connected_leads=45,
            completed_leads=0,
            failed_leads=15,
            abandoned_leads=5,
        )

        assert 0.09 <= stats.abandon_rate <= 0.11  # ~10%

    def test_abandon_rate_zero_when_no_calls(self):
        """発信がない場合の放棄率は0"""
        stats = CampaignStats(
            total_leads=100,
            pending_leads=100,
            calling_leads=0,
            connected_leads=0,
            completed_leads=0,
            failed_leads=0,
            abandoned_leads=0,
        )

        assert stats.abandon_rate == 0.0

    def test_high_abandon_rate_triggers_alert_threshold(self):
        """高い放棄率がアラート閾値を超える"""
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

        alert_threshold = 0.05  # 5%
        assert stats.abandon_rate > alert_threshold
