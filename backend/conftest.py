"""Global test fixtures for ParallelDialer."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_twilio_response() -> dict[str, Any]:
    """Mock Twilio API response."""
    return {
        "sid": "CA1234567890abcdef1234567890abcdef",
        "status": "queued",
        "direction": "outbound-api",
    }
