"""Integration tests for strategy deployment CRUD endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.helpers import seed_instrument

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


async def _create_validated_strategy_version(client: AsyncClient) -> tuple[str, str]:
    """Create a strategy and validate a version; return (strategy_id, version_id)."""
    strategy_resp = await client.post(
        "/api/v1/strategies",
        json={
            "name": f"Deploy Strategy {uuid4().hex[:6]}",
            "strategy_type": "dsl",
            "source_code": VALID_DSL,
            "parameters": {"fast_period": 3, "slow_period": 5},
        },
    )
    assert strategy_resp.status_code == 201
    strategy_id = strategy_resp.json()["data"]["id"]

    versions = await client.get(f"/api/v1/strategies/{strategy_id}/versions")
    assert versions.status_code == 200
    version_id = versions.json()["data"]["items"][0]["id"]

    validate_resp = await client.post(
        f"/api/v1/strategies/{strategy_id}/versions/{version_id}/validate"
    )
    assert validate_resp.status_code == 200
    assert validate_resp.json()["data"]["status"] == "validated"

    return strategy_id, version_id


async def _create_paper_portfolio(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/portfolios",
        json={"name": f"Deploy Portfolio {uuid4().hex[:6]}", "initial_capital": "100000"},
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_paper_broker(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/broker-connections",
        json={"broker_name": "paper", "is_paper": True, "credentials": {}},
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_list_deployments_empty(auth_client: AsyncClient, require_migrated_db):
    resp = await auth_client.get("/api/v1/strategy-deployments")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_create_deployment(auth_client: AsyncClient, require_migrated_db):
    instrument_id, _ = await seed_instrument(name="Deploy Instrument")
    _, version_id = await _create_validated_strategy_version(auth_client)
    portfolio_id = await _create_paper_portfolio(auth_client)
    broker_id = await _create_paper_broker(auth_client)

    resp = await auth_client.post(
        "/api/v1/strategy-deployments",
        json={
            "strategy_version_id": version_id,
            "portfolio_id": portfolio_id,
            "broker_connection_id": broker_id,
            "instrument_ids": [str(instrument_id)],
            "quantity": "10",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["strategy_version_id"] == version_id
    assert body["portfolio_id"] == portfolio_id
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_pause_and_resume_deployment(auth_client: AsyncClient, require_migrated_db):
    instrument_id, _ = await seed_instrument(name="Pause Instrument")
    _, version_id = await _create_validated_strategy_version(auth_client)
    portfolio_id = await _create_paper_portfolio(auth_client)
    broker_id = await _create_paper_broker(auth_client)

    create = await auth_client.post(
        "/api/v1/strategy-deployments",
        json={
            "strategy_version_id": version_id,
            "portfolio_id": portfolio_id,
            "broker_connection_id": broker_id,
            "instrument_ids": [str(instrument_id)],
            "quantity": "5",
        },
    )
    assert create.status_code == 201, create.text
    deployment_id = create.json()["data"]["id"]

    pause = await auth_client.post(f"/api/v1/strategy-deployments/{deployment_id}/pause")
    assert pause.status_code == 200, pause.text

    resume = await auth_client.post(f"/api/v1/strategy-deployments/{deployment_id}/resume")
    assert resume.status_code == 200, resume.text


@pytest.mark.asyncio
async def test_deployment_requires_validated_version(auth_client: AsyncClient, require_migrated_db):
    """Deployment of an unvalidated version should be rejected."""
    instrument_id, _ = await seed_instrument(name="Unvalidated Instrument")
    strategy_resp = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": f"Unvalidated {uuid4().hex[:6]}",
            "strategy_type": "dsl",
            "source_code": VALID_DSL,
            "parameters": {"fast_period": 3, "slow_period": 5},
        },
    )
    assert strategy_resp.status_code == 201
    strategy_id = strategy_resp.json()["data"]["id"]
    versions = await auth_client.get(f"/api/v1/strategies/{strategy_id}/versions")
    version_id = versions.json()["data"]["items"][0]["id"]

    portfolio_id = await _create_paper_portfolio(auth_client)
    broker_id = await _create_paper_broker(auth_client)

    resp = await auth_client.post(
        "/api/v1/strategy-deployments",
        json={
            "strategy_version_id": version_id,
            "portfolio_id": portfolio_id,
            "broker_connection_id": broker_id,
            "instrument_ids": [str(instrument_id)],
            "quantity": "1",
        },
    )
    assert resp.status_code in {400, 422}
