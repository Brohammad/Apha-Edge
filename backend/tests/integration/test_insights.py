from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from alphaedge.modules.insights.infrastructure.runner import execute_insight

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
async def test_insight_request_and_list(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)

    submit = await auth_client.post(
        "/api/v1/insights/strategy-explain",
        json={"strategy_version_id": version_id},
    )
    assert submit.status_code == 202
    assert submit.json()["data"]["status"] == "queued"
    assert submit.json()["data"]["id"]

    listing = await auth_client.get("/api/v1/insights")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


@pytest.mark.asyncio
async def test_strategy_explain_generates_report(auth_client: AsyncClient, require_migrated_db):
    strategy_id, version_id = await _create_validated_strategy(auth_client)

    submit = await auth_client.post(
        "/api/v1/insights/strategy-explain",
        json={"strategy_version_id": version_id},
    )
    assert submit.status_code == 202
    request_id = submit.json()["data"]["id"]

    await execute_insight(UUID(request_id))

    detail = await auth_client.get(f"/api/v1/insights/{request_id}")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["request"]["status"] == "completed"
    assert data["report"] is not None
    assert "AI Insight Report" in data["report"]["content"]
    assert data["report"]["metadata"]["model"] == "mock-llm-v1"

    await auth_client.delete(f"/api/v1/strategies/{strategy_id}")


async def _create_validated_strategy(auth_client: AsyncClient) -> tuple[str, str]:
    strategy = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": f"insight_{uuid4().hex[:6]}",
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
