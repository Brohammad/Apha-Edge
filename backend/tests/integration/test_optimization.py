from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from alphaedge.modules.optimization.infrastructure.runner import execute_optimization
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
async def test_optimization_submit_and_list(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)
    instrument_id = await _create_instrument(auth_client)

    run_id = await _submit_optimization(auth_client, version_id, instrument_id, grid_size=2)

    listing = await auth_client.get("/api/v1/optimization-runs")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/optimization-runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "queued"

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


@pytest.mark.asyncio
async def test_grid_search_optimization_full_run(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)

    symbol = f"O{uuid4().hex[:5].upper()}"
    instrument = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Optimization Test Co",
        },
    )
    instrument_id = UUID(instrument.json()["data"]["id"])
    bar_count = await seed_mock_bars(instrument_id, symbol, days=120)
    assert bar_count > 20

    run_id = await _submit_optimization(
        auth_client,
        version_id,
        str(instrument_id),
        grid_size=2,
        days=100,
    )

    await execute_optimization(UUID(run_id))

    detail = await auth_client.get(f"/api/v1/optimization-runs/{run_id}")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["status"] == "completed"
    assert data["total_trials"] == 4
    assert data["completed_trials"] == 4
    assert data["best_trial_id"] is not None

    trials = await auth_client.get(f"/api/v1/optimization-runs/{run_id}/trials")
    assert trials.status_code == 200
    trial_items = trials.json()["data"]["items"]
    assert len(trial_items) == 4
    assert all(t["status"] == "completed" for t in trial_items)

    best = await auth_client.get(f"/api/v1/optimization-runs/{run_id}/best")
    assert best.status_code == 200
    assert best.json()["data"]["rank"] == 1

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


async def _create_validated_strategy(auth_client: AsyncClient) -> tuple[str, str]:
    strategy = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": f"opt_strat_{uuid4().hex[:6]}",
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
            "symbol": f"O{uuid4().hex[:5].upper()}",
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Optimization Test",
        },
    )
    return instrument.json()["data"]["id"]


async def _submit_optimization(
    auth_client: AsyncClient,
    version_id: str,
    instrument_id: str,
    *,
    grid_size: int = 2,
    days: int = 30,
) -> str:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    fast_values = [3, 5][:grid_size]
    slow_values = [8, 12][:grid_size]
    submit = await auth_client.post(
        "/api/v1/optimization-runs",
        json={
            "strategy_version_id": version_id,
            "name": "Grid search integration test",
            "method": "grid_search",
            "objective": "sharpe_ratio",
            "parameter_space": {
                "fast_period": fast_values,
                "slow_period": slow_values,
            },
            "backtest_config": {
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
