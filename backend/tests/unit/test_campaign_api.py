"""Unit tests for Campaign API."""

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


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Get auth headers with valid token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCreateCampaign:
    """Tests for campaign creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_campaign_success(self, client: AsyncClient, auth_headers: dict):
        """キャンペーン作成成功"""
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": "テストキャンペーン", "description": "説明"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "テストキャンペーン"
        assert data["status"] == "draft"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_campaign_without_auth(self, client: AsyncClient):
        """認証なしでキャンペーン作成失敗"""
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": "テスト"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_campaign_with_custom_dial_ratio(
        self, client: AsyncClient, auth_headers: dict
    ):
        """カスタムダイヤル比率でキャンペーン作成"""
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": "テスト", "dial_ratio": 2.5},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["dial_ratio"] == 2.5

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_name(self, client: AsyncClient, auth_headers: dict):
        """無効な名前でキャンペーン作成失敗"""
        response = await client.post(
            "/api/v1/campaigns",
            json={"name": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestGetCampaign:
    """Tests for getting campaign details."""

    @pytest.mark.asyncio
    async def test_get_campaign_success(self, client: AsyncClient, auth_headers: dict):
        """キャンペーン取得成功"""
        # まずキャンペーンを作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "取得テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # キャンペーンを取得
        response = await client.get(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "取得テスト"

    @pytest.mark.asyncio
    async def test_get_nonexistent_campaign(self, client: AsyncClient, auth_headers: dict):
        """存在しないキャンペーン取得で404"""
        response = await client.get(
            "/api/v1/campaigns/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListCampaigns:
    """Tests for listing campaigns."""

    @pytest.mark.asyncio
    async def test_list_campaigns(self, client: AsyncClient, auth_headers: dict):
        """キャンペーン一覧取得"""
        # キャンペーンを作成
        await client.post(
            "/api/v1/campaigns",
            json={"name": "一覧テスト1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/campaigns",
            json={"name": "一覧テスト2"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/campaigns",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestCampaignActions:
    """Tests for campaign actions (start, pause, stop)."""

    @pytest.mark.asyncio
    async def test_start_campaign_without_leads(self, client: AsyncClient, auth_headers: dict):
        """リードなしでキャンペーン開始失敗"""
        # キャンペーン作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "開始テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # 開始試行（リードなし）
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/start",
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_start_campaign_with_leads(self, client: AsyncClient, auth_headers: dict):
        """リードありでキャンペーン開始成功"""
        # キャンペーン作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "開始テスト2"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # リード追加
        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818011112222", "name": "テスト太郎"},
            headers=auth_headers,
        )

        # 開始
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/start",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_pause_running_campaign(self, client: AsyncClient, auth_headers: dict):
        """実行中のキャンペーンを一時停止"""
        # キャンペーン作成と開始
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "一時停止テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818033334444"},
            headers=auth_headers,
        )
        await client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)

        # 一時停止
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/pause",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_stop_campaign(self, client: AsyncClient, auth_headers: dict):
        """キャンペーン停止"""
        # キャンペーン作成と開始
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "停止テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818055556666"},
            headers=auth_headers,
        )
        await client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)

        # 停止
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/stop",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"


class TestCampaignStats:
    """Tests for campaign statistics."""

    @pytest.mark.asyncio
    async def test_get_campaign_stats(self, client: AsyncClient, auth_headers: dict):
        """キャンペーン統計取得"""
        # キャンペーン作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "統計テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # リード追加
        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818077778888"},
            headers=auth_headers,
        )

        # 統計取得
        response = await client.get(
            f"/api/v1/campaigns/{campaign_id}/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "pending_leads" in data
        assert data["total_leads"] == 1


class TestAddLead:
    """Tests for adding leads to campaign."""

    @pytest.mark.asyncio
    async def test_add_lead_to_campaign(self, client: AsyncClient, auth_headers: dict):
        """キャンペーンにリード追加"""
        # キャンペーン作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "リード追加テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # リード追加
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818099990000", "name": "追加テスト"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["phone_number"] == "+818099990000"

    @pytest.mark.asyncio
    async def test_add_duplicate_lead(self, client: AsyncClient, auth_headers: dict):
        """重複リード追加で失敗"""
        # キャンペーン作成
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "重複テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        # 1回目
        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818011111111"},
            headers=auth_headers,
        )

        # 2回目（重複）
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "+818011111111"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_add_lead_invalid_phone(self, client: AsyncClient, auth_headers: dict):
        """無効な電話番号でリード追加失敗"""
        create_response = await client.post(
            "/api/v1/campaigns",
            json={"name": "無効電話テスト"},
            headers=auth_headers,
        )
        campaign_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads",
            json={"phone_number": "08011112222"},  # +なし
            headers=auth_headers,
        )
        assert response.status_code == 422
