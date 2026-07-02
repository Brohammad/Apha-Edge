from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from alphaedge.main import app


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"md_{uuid4().hex[:8]}@alphaedge.io"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "securepass123", "display_name": "MD Tester"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "securepass123"},
        )
        token = login.json()["data"]["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
@patch("alphaedge.modules.market_data.infrastructure.tasks.run_ingestion_task")
async def test_market_data_endpoints(mock_task, auth_client, require_migrated_db):
    mock_task.delay.return_value = MagicMock(id="task-123")

    symbol = f"T{uuid4().hex[:6].upper()}"

    create = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Tesla Inc.",
        },
    )
    assert create.status_code == 201
    instrument_id = create.json()["data"]["id"]

    listing = await auth_client.get("/api/v1/instruments")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/instruments/{instrument_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["symbol"] == symbol

    end = datetime.now(UTC)
    start = end - timedelta(days=7)
    ingest = await auth_client.post(
        "/api/v1/market-data/ingest",
        json={
            "provider": "mock",
            "symbols": [symbol],
            "timeframe": "1d",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    assert ingest.status_code == 202
    job_id = ingest.json()["data"]["id"]

    job = await auth_client.get(f"/api/v1/market-data/ingest/{job_id}")
    assert job.status_code == 200
    assert job.json()["data"]["provider"] == "mock"
