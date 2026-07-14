"""Integration test: bar ingestion triggers deployment signal and paper order."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from alphaedge.modules.execution.infrastructure.runner import execute_order
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyBarRepository
from alphaedge.modules.strategy.infrastructure.deployment_runner import evaluate_deployments_for_bar
from alphaedge.shared.infrastructure.database import async_session_factory
from tests.helpers import seed_instrument, seed_mock_bars

pytestmark = pytest.mark.integration

ALWAYS_BUY_PYTHON = """
from alphaedge.modules.strategy.domain.indicators import StrategyBase
from alphaedge.modules.strategy.domain.value_objects import Signal
from alphaedge.modules.strategy.domain.enums import SignalAction

class AlwaysBuy(StrategyBase):
    def on_bar(self, bar, context):
        return Signal(action=SignalAction.BUY, reason="integration-test")
"""


async def _create_validated_python_version(client: AsyncClient) -> str:
    strategy_resp = await client.post(
        "/api/v1/strategies",
        json={
            "name": f"Signal Flow {uuid4().hex[:6]}",
            "strategy_type": "python",
            "source_code": ALWAYS_BUY_PYTHON,
            "parameters": {},
        },
    )
    assert strategy_resp.status_code == 201
    strategy_id = strategy_resp.json()["data"]["id"]
    versions = await client.get(f"/api/v1/strategies/{strategy_id}/versions")
    version_id = versions.json()["data"]["items"][0]["id"]
    validate_resp = await client.post(
        f"/api/v1/strategies/{strategy_id}/versions/{version_id}/validate"
    )
    assert validate_resp.status_code == 200
    assert validate_resp.json()["data"]["status"] == "validated"
    return version_id


@pytest.mark.asyncio
async def test_bar_triggers_deployment_signal_and_paper_order(
    auth_client: AsyncClient, require_migrated_db
):
    instrument_id, _ = await seed_instrument(name="Signal Flow Instrument")
    await seed_mock_bars(instrument_id, "SIGFLOW", days=30)

    version_id = await _create_validated_python_version(auth_client)

    portfolio_resp = await auth_client.post(
        "/api/v1/portfolios",
        json={"name": f"Signal Portfolio {uuid4().hex[:6]}", "initial_capital": "100000"},
    )
    assert portfolio_resp.status_code == 201
    portfolio_id = portfolio_resp.json()["data"]["id"]

    broker_resp = await auth_client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True, "credentials": {}},
    )
    assert broker_resp.status_code == 201
    broker_id = broker_resp.json()["data"]["id"]

    deploy_resp = await auth_client.post(
        "/api/v1/strategy-deployments",
        json={
            "strategy_version_id": version_id,
            "portfolio_id": portfolio_id,
            "broker_connection_id": broker_id,
            "instrument_ids": [str(instrument_id)],
            "quantity": "3",
        },
    )
    assert deploy_resp.status_code == 201, deploy_resp.text

    async with async_session_factory() as session:
        bar_repo = SQLAlchemyBarRepository(session)
        bar = await bar_repo.get_latest(instrument_id, Timeframe.D1)
        assert bar is not None

    orders_submitted = await evaluate_deployments_for_bar(bar)
    assert orders_submitted == 1

    orders_resp = await auth_client.get(f"/api/v1/orders?portfolio_id={portfolio_id}")
    assert orders_resp.status_code == 200
    items = orders_resp.json()["data"]["items"]
    assert len(items) >= 1
    order_id = items[0]["id"]
    assert items[0]["side"] == "buy"
    assert float(items[0]["quantity"]) == 3

    await execute_order(UUID(order_id))

    filled = await auth_client.get(f"/api/v1/orders/{order_id}")
    assert filled.status_code == 200
    assert filled.json()["data"]["status"] == "filled"
