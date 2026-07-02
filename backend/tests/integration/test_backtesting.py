from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from alphaedge.main import app

VALID_DSL = """
name: sma_crossover
parameters:
  fast_period: 3
  slow_period: 5
signals:
  - when: crossover(sma(fast_period), sma(slow_period))
    then: BUY
  - when: crossunder(sma(fast_period), sma(slow_period))
    then: SELL
"""


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"bt_{uuid4().hex[:8]}@alphaedge.io"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "securepass123", "display_name": "BT Tester"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "securepass123"},
        )
        token = login.json()["data"]["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
@patch("alphaedge.modules.backtesting.presentation.router.run_backtest_task")
async def test_backtest_endpoints(mock_task, auth_client, require_migrated_db):
    mock_task.delay.return_value = MagicMock(id="bt-task-123")

    strategy = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": f"bt_strat_{uuid4().hex[:6]}",
            "strategy_type": "dsl",
            "source_code": VALID_DSL,
            "parameters": {"fast_period": 3, "slow_period": 5},
        },
    )
    assert strategy.status_code == 201
    strategy_id = strategy.json()["data"]["id"]

    versions = await auth_client.get(f"/api/v1/strategies/{strategy_id}/versions")
    version_id = versions.json()["data"]["items"][0]["id"]

    validate = await auth_client.post(
        f"/api/v1/strategies/{strategy_id}/versions/{version_id}/validate"
    )
    assert validate.status_code == 200
    assert validate.json()["data"]["status"] == "validated"

    instrument = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": f"B{uuid4().hex[:5].upper()}",
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Backtest Test Co",
        },
    )
    instrument_id = instrument.json()["data"]["id"]

    end = datetime.now(UTC)
    start = end - timedelta(days=30)

    submit = await auth_client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_version_id": version_id,
            "name": "Integration backtest",
            "config": {
                "instrument_ids": [instrument_id],
                "timeframe": "1d",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "initial_capital": "100000",
                "slippage": {"model": "fixed", "value": "0.01"},
                "commission": {"per_trade": "1.0"},
                "position_sizing": {"model": "percent_equity", "value": "0.1"},
            },
        },
    )
    assert submit.status_code == 202
    run_id = submit.json()["data"]["id"]

    listing = await auth_client.get("/api/v1/backtest-runs")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/backtest-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "queued"

    delete = await auth_client.delete(f"/api/v1/backtest-runs/{run_id}")
    assert delete.status_code == 204
