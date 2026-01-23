"""Unit tests for Lead Import API."""

import io
import pytest
from httpx import AsyncClient

from app.main import app
from app.api.v1.campaigns import CAMPAIGNS_DB


@pytest.fixture
async def client():
    """Create async HTTP client for testing."""
    from httpx import ASGITransport

    # Clear campaigns between tests
    CAMPAIGNS_DB.clear()

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


@pytest.fixture
async def campaign_id(client: AsyncClient, auth_headers: dict) -> str:
    """Create a campaign and return its ID."""
    response = await client.post(
        "/api/v1/campaigns",
        json={"name": "Import Test Campaign"},
        headers=auth_headers,
    )
    return response.json()["id"]


class TestCSVImport:
    """Tests for CSV import functionality."""

    @pytest.mark.asyncio
    async def test_import_csv_utf8(self, client: AsyncClient, auth_headers: dict, campaign_id: str):
        """UTF-8 CSVをインポート"""
        csv_content = "phone_number,name,company\n+818011111111,田中太郎,株式会社A\n+818022222222,鈴木花子,株式会社B"
        files = {"file": ("leads.csv", csv_content.encode("utf-8"), "text/csv")}

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2
        assert data["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_import_csv_shift_jis(
        self, client: AsyncClient, auth_headers: dict, campaign_id: str
    ):
        """Shift_JIS CSVをインポート（自動検出）"""
        csv_content = "phone_number,name,company\n+818033333333,山田太郎,株式会社C"
        files = {"file": ("leads.csv", csv_content.encode("shift_jis"), "text/csv")}

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 1

    @pytest.mark.asyncio
    async def test_import_skips_duplicates(
        self, client: AsyncClient, auth_headers: dict, campaign_id: str
    ):
        """重複電話番号をスキップ"""
        # 1回目のインポート
        csv_content1 = "phone_number,name\n+818044444444,First"
        files1 = {"file": ("leads1.csv", csv_content1.encode("utf-8"), "text/csv")}
        await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files1,
            headers=auth_headers,
        )

        # 2回目（重複あり）
        csv_content2 = "phone_number,name\n+818044444444,Duplicate\n+818055555555,New"
        files2 = {"file": ("leads2.csv", csv_content2.encode("utf-8"), "text/csv")}
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files2,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 1
        assert data["skipped_count"] == 1

    @pytest.mark.asyncio
    async def test_import_skips_invalid_phones(
        self, client: AsyncClient, auth_headers: dict, campaign_id: str
    ):
        """無効な電話番号をスキップ"""
        csv_content = "phone_number,name\n08066666666,Invalid\n+818077777777,Valid"
        files = {"file": ("leads.csv", csv_content.encode("utf-8"), "text/csv")}

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 1
        assert data["skipped_count"] == 1
        assert len(data["errors"]) == 1

    @pytest.mark.asyncio
    async def test_import_empty_file(
        self, client: AsyncClient, auth_headers: dict, campaign_id: str
    ):
        """空ファイルでエラー"""
        files = {"file": ("empty.csv", b"", "text/csv")}

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_import_missing_phone_column(
        self, client: AsyncClient, auth_headers: dict, campaign_id: str
    ):
        """phone_number列がないCSVでエラー"""
        csv_content = "name,company\n田中,株式会社A"
        files = {"file": ("leads.csv", csv_content.encode("utf-8"), "text/csv")}

        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/leads/import",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "phone_number" in response.json()["detail"].lower()
