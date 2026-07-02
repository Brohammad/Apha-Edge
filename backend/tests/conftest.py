import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alphaedge.config import settings
from alphaedge.main import app

REQUIRED_TABLES = ("users", "instruments", "strategies", "strategy_versions", "backtest_runs")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests requiring Postgres (and optionally Redis)",
    )


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def require_migrated_db():
    """Skip integration tests when Postgres is down or migrations are missing."""

    async def check() -> None:
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as conn:
                for table in REQUIRED_TABLES:
                    await conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
        finally:
            await engine.dispose()

    try:
        asyncio.run(check())
    except Exception as exc:
        pytest.skip(f"Database unavailable or migrations not applied: {exc}")


@pytest.fixture(scope="session")
def require_redis():
    """Skip when Redis is unavailable (health/ready tests)."""

    async def check() -> None:
        from alphaedge.shared.infrastructure.redis import check_redis_health, close_redis

        try:
            if not await check_redis_health():
                raise ConnectionError("Redis ping failed")
        finally:
            await close_redis()

    try:
        asyncio.run(check())
    except Exception as exc:
        pytest.skip(f"Redis unavailable: {exc}")


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client() -> AsyncGenerator[AsyncClient, None]:
    """Authenticated HTTP client backed by a freshly registered user."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = f"test_{uuid4().hex[:8]}@alphaedge.io"
        await ac.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "securepass123", "display_name": "Test User"},
        )
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "securepass123"},
        )
        token = login.json()["data"]["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
