from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def require_migrated_db():
    """Skip integration tests when Postgres is down or migrations are missing."""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            for table in REQUIRED_TABLES:
                await conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Database unavailable or migrations not applied: {exc}")
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def require_redis():
    """Skip when Redis is unavailable (health/ready tests)."""
    from alphaedge.shared.infrastructure.redis import check_redis_health, close_redis

    try:
        if not await check_redis_health():
            pytest.skip("Redis unavailable")
    except Exception as exc:
        pytest.skip(f"Redis unavailable: {exc}")
    finally:
        await close_redis()


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
