"""Unit tests for Auth API."""

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


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, client: AsyncClient):
        """有効な認証情報でログイン成功"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_with_invalid_password(self, client: AsyncClient):
        """無効なパスワードでログイン失敗"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_login_with_nonexistent_user(self, client: AsyncClient):
        """存在しないユーザーでログイン失敗"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody", "password": "password"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient):
        """有効なリフレッシュトークンで更新成功"""
        # まずログインしてトークンを取得
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # リフレッシュトークンで新しいアクセストークンを取得
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """無効なリフレッシュトークンで失敗"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401


class TestProtectedEndpoint:
    """Tests for protected endpoints."""

    @pytest.mark.asyncio
    async def test_access_protected_with_valid_token(self, client: AsyncClient):
        """有効なトークンで保護されたエンドポイントにアクセス"""
        # ログインしてトークンを取得
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        access_token = login_response.json()["access_token"]

        # トークンを使ってアクセス
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_access_protected_without_token(self, client: AsyncClient):
        """トークンなしで保護されたエンドポイントにアクセス失敗"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_with_expired_token(self, client: AsyncClient):
        """期限切れトークンでアクセス失敗"""
        # 期限切れのトークン（実際には無効なトークン）
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MX0.invalid"

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
