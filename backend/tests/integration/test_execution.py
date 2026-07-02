from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from alphaedge.modules.execution.infrastructure.runner import execute_order
from tests.helpers import seed_mock_bars

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_broker_connection_crud(auth_client: AsyncClient, require_migrated_db):
    create = await auth_client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True},
    )
    assert create.status_code == 201
    connection_id = create.json()["data"]["id"]

    listing = await auth_client.get("/api/v1/broker-connections")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    delete = await auth_client.delete(f"/api/v1/broker-connections/{connection_id}")
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_market_order_submit_fill_and_executions(
    auth_client: AsyncClient, require_migrated_db
):
    portfolio_id = await _create_portfolio(auth_client)
    connection_id = await _create_broker_connection(auth_client)
    instrument_id = await _create_instrument_with_bars(auth_client)

    submit = await auth_client.post(
        "/api/v1/orders",
        json={
            "portfolio_id": portfolio_id,
            "broker_connection_id": connection_id,
            "instrument_id": instrument_id,
            "side": "buy",
            "order_type": "market",
            "quantity": "10",
            "idempotency_key": f"order-{uuid4().hex}",
        },
    )
    assert submit.status_code == 202
    order_id = submit.json()["data"]["id"]

    await execute_order(UUID(order_id))

    detail = await auth_client.get(f"/api/v1/orders/{order_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "filled"
    assert float(detail.json()["data"]["filled_quantity"]) == 10

    executions = await auth_client.get(f"/api/v1/orders/{order_id}/executions")
    assert executions.status_code == 200
    assert executions.json()["data"]["total_count"] == 1

    holdings = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/holdings")
    assert holdings.status_code == 200
    assert holdings.json()["data"]["total_count"] == 1

    listing = await auth_client.get("/api/v1/orders")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1


@pytest.mark.asyncio
async def test_order_idempotency(auth_client: AsyncClient, require_migrated_db):
    portfolio_id = await _create_portfolio(auth_client)
    connection_id = await _create_broker_connection(auth_client)
    instrument_id = await _create_instrument_with_bars(auth_client)
    idempotency_key = f"idem-{uuid4().hex}"

    payload = {
        "portfolio_id": portfolio_id,
        "broker_connection_id": connection_id,
        "instrument_id": instrument_id,
        "side": "buy",
        "order_type": "market",
        "quantity": "5",
        "idempotency_key": idempotency_key,
    }
    first = await auth_client.post("/api/v1/orders", json=payload)
    second = await auth_client.post("/api/v1/orders", json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


@pytest.mark.asyncio
async def test_cancel_pending_order(auth_client: AsyncClient, require_migrated_db):
    portfolio_id = await _create_portfolio(auth_client)
    connection_id = await _create_broker_connection(auth_client)
    instrument_id = await _create_instrument(auth_client)

    submit = await auth_client.post(
        "/api/v1/orders",
        json={
            "portfolio_id": portfolio_id,
            "broker_connection_id": connection_id,
            "instrument_id": instrument_id,
            "side": "buy",
            "order_type": "limit",
            "quantity": "10",
            "limit_price": "1.00",
        },
    )
    assert submit.status_code == 202
    order_id = submit.json()["data"]["id"]

    cancel = await auth_client.delete(f"/api/v1/orders/{order_id}")
    assert cancel.status_code == 200
    assert cancel.json()["data"]["status"] == "cancelled"


async def _create_portfolio(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/api/v1/portfolios",
        json={
            "name": f"exec_{uuid4().hex[:6]}",
            "initial_capital": "100000",
            "base_currency": "USD",
            "is_paper": True,
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_broker_connection(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True},
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_instrument(auth_client: AsyncClient) -> str:
    resp = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": f"E{uuid4().hex[:5].upper()}",
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Execution Test Co",
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_instrument_with_bars(auth_client: AsyncClient) -> str:
    symbol = f"E{uuid4().hex[:5].upper()}"
    resp = await auth_client.post(
        "/api/v1/instruments",
        json={
            "symbol": symbol,
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
            "name": "Execution Test Co",
        },
    )
    instrument_id = UUID(resp.json()["data"]["id"])
    count = await seed_mock_bars(instrument_id, symbol, days=30)
    assert count > 0
    return str(instrument_id)
