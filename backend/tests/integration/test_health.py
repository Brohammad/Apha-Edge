import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient, require_migrated_db, require_redis):
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_openapi_docs_available(client: AsyncClient):
    response = await client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "AlphaEdge API"
    paths = schema["paths"]
    for path in (
        "/api/v1/auth/register",
        "/api/v1/instruments",
        "/api/v1/strategies",
        "/api/v1/backtest-runs",
        "/api/v1/indicators",
    ):
        assert path in paths, f"Missing route: {path}"
