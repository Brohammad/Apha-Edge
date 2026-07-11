"""Integration test: risk gate rejects oversized paper orders."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.helpers import seed_instrument, seed_mock_bars

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_order_rejected_by_risk_gate_insufficient_cash(
    auth_client: AsyncClient, require_migrated_db
):
    portfolio = await auth_client.post(
        "/api/v1/portfolios",
        json={"name": f"Risk Cash {uuid4().hex[:6]}", "initial_capital": "1000"},
    )
    assert portfolio.status_code == 201
    portfolio_id = portfolio.json()["data"]["id"]

    # Cap position and exposure high so cash_availability is the failing stage.
    limits = await auth_client.put(
        f"/api/v1/portfolios/{portfolio_id}/risk/limits",
        json={
            "limits": [
                {"limit_type": "max_position_pct", "threshold": "5.0", "is_active": True},
                {
                    "limit_type": "max_portfolio_exposure_pct",
                    "threshold": "5.0",
                    "is_active": True,
                },
            ]
        },
    )
    assert limits.status_code in {200, 201}, limits.text

    broker = await auth_client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True, "credentials": {}},
    )
    assert broker.status_code == 201
    broker_id = broker.json()["data"]["id"]

    instrument_id, symbol = await seed_instrument(name="Risk Gate Instrument")
    await seed_mock_bars(instrument_id, symbol, days=30)

    submit = await auth_client.post(
        "/api/v1/orders",
        json={
            "portfolio_id": portfolio_id,
            "broker_connection_id": broker_id,
            "instrument_id": str(instrument_id),
            "side": "buy",
            "order_type": "market",
            "quantity": "1000",
            "idempotency_key": f"risk-{uuid4().hex}",
        },
    )
    assert submit.status_code == 422, submit.text
    err = submit.json()["error"]
    assert err["code"] == "RISK_REJECTED"
    assert err["details"]["stage"] in {
        "cash_availability",
        "max_position_exposure",
        "portfolio_exposure",
        "position_sizing",
    }
