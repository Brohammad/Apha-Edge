from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from alphaedge.modules.backtesting.infrastructure.runner import execute_backtest
from tests.helpers import seed_mock_bars

pytestmark = pytest.mark.integration

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


@pytest.mark.asyncio
async def test_backtest_submit_and_cancel(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)

    instrument_id = await _create_instrument(auth_client)
    run_id = await _submit_backtest(auth_client, version_id, instrument_id)

    listing = await auth_client.get("/api/v1/backtest-runs")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/backtest-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "queued"

    delete = await auth_client.delete(f"/api/v1/backtest-runs/{run_id}")
    assert delete.status_code == 204

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


@pytest.mark.asyncio
async def test_backtest_full_run_with_results(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)

    symbol = f"X{uuid4().hex[:5].upper()}"
    instrument = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Backtest Full Run",
        },
    )
    instrument_id = UUID(instrument.json()["data"]["id"])
    bar_count = await seed_mock_bars(instrument_id, symbol, days=120)
    assert bar_count > 20

    end = datetime.now(UTC)
    start = end - timedelta(days=100)
    with patch("alphaedge.modules.backtesting.presentation.router.run_backtest_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="test-celery-id")
        submit = await auth_client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_version_id": version_id,
                "name": "Full integration backtest",
                "config": {
                    "instrument_ids": [str(instrument_id)],
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

    await execute_backtest(UUID(run_id))

    detail = await auth_client.get(f"/api/v1/backtest-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "completed"

    result = await auth_client.get(f"/api/v1/backtest-runs/{run_id}/result")
    assert result.status_code == 200
    assert result.json()["data"]["total_trades"] >= 0
    assert result.json()["data"]["max_drawdown"] is not None

    curve = await auth_client.get(f"/api/v1/backtest-runs/{run_id}/equity-curve")
    assert curve.status_code == 200
    assert curve.json()["data"]["total_count"] > 0

    trades = await auth_client.get(f"/api/v1/backtest-runs/{run_id}/trades")
    assert trades.status_code == 200

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


async def _create_validated_strategy(auth_client: AsyncClient) -> tuple[str, str]:
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
    assert validate.json()["data"]["status"] == "validated"
    return strategy_id, version_id


async def _create_instrument(auth_client: AsyncClient) -> str:
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
    return instrument.json()["data"]["id"]


async def _submit_backtest(auth_client: AsyncClient, version_id: str, instrument_id: str) -> str:
    end = datetime.now(UTC)
    start = end - timedelta(days=30)
    with patch("alphaedge.modules.backtesting.presentation.router.run_backtest_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="test-celery-id")
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
    return submit.json()["data"]["id"]
