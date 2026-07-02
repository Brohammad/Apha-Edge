from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_portfolio_crud_and_risk_flow(auth_client: AsyncClient, require_migrated_db):
    create = await auth_client.post(
        "/api/v1/portfolios",
        json={
            "name": f"portfolio_{uuid4().hex[:6]}",
            "initial_capital": "100000",
            "base_currency": "USD",
            "is_paper": True,
        },
    )
    assert create.status_code == 201
    portfolio_id = create.json()["data"]["id"]
    assert create.json()["data"]["cash_balance"] == "100000"

    listing = await auth_client.get("/api/v1/portfolios")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["name"].startswith("portfolio_")

    holdings = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/holdings")
    assert holdings.status_code == 200
    assert holdings.json()["data"]["total_count"] == 0

    perf = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
    assert perf.status_code == 200
    assert perf.json()["data"]["total_value"] == "100000"

    rebalance = await auth_client.post(
        f"/api/v1/portfolios/{portfolio_id}/rebalance",
        json={"target_allocation": {"AAPL": 0.6, "MSFT": 0.4}},
    )
    assert rebalance.status_code == 201
    plan_id = rebalance.json()["data"]["id"]
    assert rebalance.json()["data"]["status"] == "draft"

    plan = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/rebalance/{plan_id}")
    assert plan.status_code == 200

    limits = await auth_client.put(
        f"/api/v1/portfolios/{portfolio_id}/risk/limits",
        json={
            "limits": [
                {"limit_type": "max_drawdown", "threshold": "0.25", "is_active": True},
                {"limit_type": "max_var", "threshold": "0.10", "is_active": True},
            ]
        },
    )
    assert limits.status_code == 200
    assert len(limits.json()["data"]["items"]) == 2

    get_limits = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/risk/limits")
    assert get_limits.status_code == 200

    compute = await auth_client.post(f"/api/v1/portfolios/{portfolio_id}/risk/compute")
    assert compute.status_code == 201
    assert compute.json()["data"]["max_drawdown"] is not None

    latest = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/risk/snapshots/latest")
    assert latest.status_code == 200

    snapshots = await auth_client.get(f"/api/v1/portfolios/{portfolio_id}/risk/snapshots")
    assert snapshots.status_code == 200
    assert snapshots.json()["data"]["total_count"] >= 1
