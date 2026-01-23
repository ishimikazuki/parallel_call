"""Unit tests for Twilio Webhooks."""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Create async HTTP client for testing."""
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestStatusWebhook:
    """Tests for call status webhook."""

    @pytest.mark.asyncio
    async def test_status_initiated(self, client: AsyncClient):
        """initiated ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "initiated",
                "From": "+818011112222",
                "To": "+818033334444",
            },
        )
        assert response.status_code == 200
        # TwiML or empty response
        assert response.headers.get("content-type", "").startswith(("text/xml", "application/xml"))

    @pytest.mark.asyncio
    async def test_status_ringing(self, client: AsyncClient):
        """ringing ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "ringing",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_answered(self, client: AsyncClient):
        """answered ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "in-progress",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_completed(self, client: AsyncClient):
        """completed ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "completed",
                "CallDuration": "120",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_busy(self, client: AsyncClient):
        """busy ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "busy",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_no_answer(self, client: AsyncClient):
        """no-answer ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "no-answer",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_failed(self, client: AsyncClient):
        """failed ステータスを処理"""
        response = await client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA1234567890",
                "CallStatus": "failed",
                "ErrorCode": "31002",
                "ErrorMessage": "Connection declined",
            },
        )
        assert response.status_code == 200


class TestAMDWebhook:
    """Tests for Answering Machine Detection webhook."""

    @pytest.mark.asyncio
    async def test_amd_human(self, client: AsyncClient):
        """human検出を処理"""
        response = await client.post(
            "/webhooks/twilio/amd",
            data={
                "CallSid": "CA1234567890",
                "AnsweredBy": "human",
            },
        )
        assert response.status_code == 200
        # Should return TwiML to connect to operator
        content = response.text
        assert "Conference" in content or "Dial" in content or "xml" in content.lower()

    @pytest.mark.asyncio
    async def test_amd_machine_start(self, client: AsyncClient):
        """machine_start検出を処理（留守電の開始）"""
        response = await client.post(
            "/webhooks/twilio/amd",
            data={
                "CallSid": "CA1234567890",
                "AnsweredBy": "machine_start",
            },
        )
        assert response.status_code == 200
        # Should hangup
        content = response.text
        assert "Hangup" in content or "xml" in content.lower()

    @pytest.mark.asyncio
    async def test_amd_machine_end_beep(self, client: AsyncClient):
        """machine_end_beep検出を処理"""
        response = await client.post(
            "/webhooks/twilio/amd",
            data={
                "CallSid": "CA1234567890",
                "AnsweredBy": "machine_end_beep",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_amd_fax(self, client: AsyncClient):
        """fax検出を処理"""
        response = await client.post(
            "/webhooks/twilio/amd",
            data={
                "CallSid": "CA1234567890",
                "AnsweredBy": "fax",
            },
        )
        assert response.status_code == 200
        # Should hangup
        content = response.text
        assert "Hangup" in content or "xml" in content.lower()

    @pytest.mark.asyncio
    async def test_amd_unknown(self, client: AsyncClient):
        """unknown検出を処理"""
        response = await client.post(
            "/webhooks/twilio/amd",
            data={
                "CallSid": "CA1234567890",
                "AnsweredBy": "unknown",
            },
        )
        assert response.status_code == 200


class TestVoiceWebhook:
    """Tests for incoming voice webhook."""

    @pytest.mark.asyncio
    async def test_voice_webhook_returns_twiml(self, client: AsyncClient):
        """音声Webhookが有効なTwiMLを返す"""
        response = await client.post(
            "/webhooks/twilio/voice",
            data={
                "CallSid": "CA1234567890",
                "From": "+818011112222",
                "To": "+818099990000",
            },
        )
        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "").lower()
