"""Full-stack end-to-end test against a running API (HTTP, Postgres, Redis, Celery)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from tests.e2e.conftest import wait_for_status
from tests.helpers import seed_instrument, seed_mock_bars

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

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
async def test_full_platform_journey(e2e_auth_client: httpx.AsyncClient):
    """Exercise auth, strategy, backtest, portfolio, execution, and marketplace flows."""
    client = e2e_auth_client

    # --- Auth & session ---
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    user = me.json()["data"]
    assert user["email"].endswith("@alphaedge.io")
    assert user["email_verified"] is True

    ws_ticket = await client.post("/api/v1/auth/ws-ticket")
    assert ws_ticket.status_code == 200
    assert ws_ticket.json()["data"]["ticket"]

    refresh = await client.post("/api/v1/auth/refresh", json={})
    assert refresh.status_code == 200
    new_token = refresh.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {new_token}"

    # --- API keys ---
    api_key_resp = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "E2E key", "scopes": ["read:*"], "rate_limit_tier": "standard"},
    )
    assert api_key_resp.status_code == 201
    raw_key = api_key_resp.json()["data"]["key"]
    key_id = api_key_resp.json()["data"]["api_key"]["id"]

    key_client = httpx.AsyncClient(
        base_url=str(client.base_url),
        headers={"X-API-Key": raw_key},
        timeout=30.0,
    )
    try:
        key_me = await key_client.get("/api/v1/auth/me")
        assert key_me.status_code == 200
    finally:
        await key_client.aclose()

    # --- Organization ---
    org_slug = f"e2e-org-{uuid4().hex[:8]}"
    org = await client.post(
        "/api/v1/organizations",
        json={"name": "E2E Desk", "slug": org_slug},
    )
    assert org.status_code == 201
    org_id = org.json()["data"]["id"]

    # --- Strategy lifecycle ---
    strategy_name = f"e2e_strat_{uuid4().hex[:6]}"
    strategy = await client.post(
        "/api/v1/strategies",
        json={
            "name": strategy_name,
            "strategy_type": "dsl",
            "description": "E2E crossover",
            "source_code": VALID_DSL,
            "parameters": {"fast_period": 3, "slow_period": 5},
        },
    )
    assert strategy.status_code == 201
    strategy_id = strategy.json()["data"]["id"]

    versions = await client.get(f"/api/v1/strategies/{strategy_id}/versions")
    version_id = versions.json()["data"]["items"][0]["id"]

    validate = await client.post(f"/api/v1/strategies/{strategy_id}/versions/{version_id}/validate")
    assert validate.status_code == 200
    assert validate.json()["data"]["status"] == "validated"

    indicators = await client.get("/api/v1/indicators")
    assert indicators.status_code == 200
    indicator_names = {i["name"] for i in indicators.json()["data"]["items"]}
    assert "sma" in indicator_names

    # --- Instrument + backtest (async via Celery) ---
    instrument_id, symbol = await seed_instrument(name="E2E Test Instrument")
    bar_count = await seed_mock_bars(instrument_id, symbol, days=90)
    assert bar_count > 20

    end = datetime.now(UTC)
    start = end - timedelta(days=60)
    backtest = await client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_version_id": version_id,
            "name": "E2E backtest",
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
    assert backtest.status_code == 202
    run_id = backtest.json()["data"]["id"]

    await wait_for_status(client, f"/api/v1/backtest-runs/{run_id}", expected="completed")

    result = await client.get(f"/api/v1/backtest-runs/{run_id}/result")
    assert result.status_code == 200
    assert result.json()["data"]["max_drawdown"] is not None

    # --- Portfolio + paper execution ---
    portfolio = await client.post(
        "/api/v1/portfolios",
        json={
            "name": f"e2e_pf_{uuid4().hex[:6]}",
            "initial_capital": "100000",
            "base_currency": "USD",
            "is_paper": True,
        },
    )
    assert portfolio.status_code == 201
    portfolio_id = portfolio.json()["data"]["id"]

    broker = await client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True},
    )
    assert broker.status_code == 201
    connection_id = broker.json()["data"]["id"]

    order = await client.post(
        "/api/v1/orders",
        json={
            "portfolio_id": portfolio_id,
            "broker_connection_id": connection_id,
            "instrument_id": str(instrument_id),
            "side": "buy",
            "order_type": "market",
            "quantity": "10",
            "idempotency_key": f"e2e-{uuid4().hex}",
        },
    )
    assert order.status_code == 202
    order_id = order.json()["data"]["id"]

    filled = await wait_for_status(client, f"/api/v1/orders/{order_id}", expected="filled")
    assert float(filled["filled_quantity"]) == 10

    holdings = await client.get(f"/api/v1/portfolios/{portfolio_id}/holdings")
    assert holdings.status_code == 200
    assert holdings.json()["data"]["total_count"] >= 1

    # --- Marketplace ---
    listing = await client.post(
        "/api/v1/marketplace/listings",
        json={
            "strategy_id": strategy_id,
            "organization_id": org_id,
            "title": "E2E Golden Cross",
            "description": "Published during e2e",
            "price_cents": 0,
        },
    )
    assert listing.status_code == 201
    listing_id = listing.json()["data"]["id"]

    public = await client.get("/api/v1/marketplace/listings")
    assert any(i["id"] == listing_id for i in public.json()["data"]["items"])

    clone = await client.post(f"/api/v1/marketplace/listings/{listing_id}/clone")
    assert clone.status_code == 201

    # --- Cleanup ---
    revoke = await client.delete(f"/api/v1/auth/api-keys/{key_id}")
    assert revoke.status_code == 204

    logout = await client.post("/api/v1/auth/logout", json={})
    assert logout.status_code == 204
