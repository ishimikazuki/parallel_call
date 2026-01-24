"""Global test fixtures for ParallelDialer."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
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


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _init_test_db(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _drop_test_db(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> None:
    """Initialize and tear down the test database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    asyncio.run(_init_test_db(engine))
    app.dependency_overrides[get_session] = override_get_session

    yield

    app.dependency_overrides.clear()
    asyncio.run(_drop_test_db(engine))
    asyncio.run(engine.dispose())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-apply test markers based on directory."""
    for item in items:
        path = Path(str(item.fspath))
        parts = path.parts
        if "tests" in parts:
            if "unit" in parts:
                item.add_marker(pytest.mark.unit)
            elif "e2e" in parts:
                item.add_marker(pytest.mark.e2e)
            elif "integration" in parts:
                item.add_marker(pytest.mark.integration)
