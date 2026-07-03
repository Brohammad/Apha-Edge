import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import sql

from alphaedge.config import settings
from alphaedge.main import app
from alphaedge.shared.infrastructure.logging import setup_logging

REQUIRED_TABLES = (
    "users",
    "instruments",
    "strategies",
    "strategy_versions",
    "backtest_runs",
    "optimization_runs",
    "oauth_accounts",
    "api_keys",
    "organizations",
    "strategy_listings",
    "strategy_collab_sessions",
    "broker_connections",
    "orders",
    "insight_requests",
    "portfolios",
)


@asynccontextmanager
async def _test_lifespan(_app: object):
    """Test lifespan: skip engine/redis teardown on each HTTP client exit."""
    setup_logging()
    yield


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limit_for_tests() -> None:
    """Integration tests share one ASGI client IP; disable app rate limits in pytest."""
    from alphaedge.config import settings

    settings.rate_limit_enabled = False


@pytest.fixture(scope="session", autouse=True)
def _patch_app_lifespan_for_tests() -> None:
    app.router.lifespan_context = _test_lifespan  # type: ignore[assignment]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests requiring Postgres (and optionally Redis)",
    )


def _postgres_dsn() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def require_migrated_db() -> None:
    """Skip integration tests when Postgres is down or migrations are missing."""
    try:
        with (
            psycopg.connect(_postgres_dsn(), connect_timeout=3) as conn,
            conn.cursor() as cur,
        ):
            for table in REQUIRED_TABLES:
                cur.execute(sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table)))
    except Exception as exc:
        pytest.skip(f"Database unavailable or migrations not applied: {exc}")


@pytest.fixture(scope="session")
def require_redis() -> None:
    """Skip when Redis is unavailable (health/ready tests)."""
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
    except OSError as exc:
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
