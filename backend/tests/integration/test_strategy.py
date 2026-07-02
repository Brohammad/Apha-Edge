from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from alphaedge.main import app

VALID_DSL = """
name: sma_crossover
parameters:
  fast_period: 10
  slow_period: 30
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
        email = f"st_{uuid4().hex[:8]}@alphaedge.io"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "securepass123", "display_name": "Strategy Tester"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "securepass123"},
        )
        token = login.json()["data"]["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
async def test_strategy_endpoints(auth_client, require_migrated_db):
    name = f"strategy_{uuid4().hex[:8]}"

    create = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": name,
            "strategy_type": "dsl",
            "description": "SMA crossover test",
            "source_code": VALID_DSL,
            "parameters": {"fast_period": 10, "slow_period": 30},
        },
    )
    assert create.status_code == 201
    strategy_id = create.json()["data"]["id"]
    assert create.json()["data"]["strategy_type"] == "dsl"

    listing = await auth_client.get("/api/v1/strategies")
    assert listing.status_code == 200
    assert listing.json()["data"]["total_count"] >= 1

    detail = await auth_client.get(f"/api/v1/strategies/{strategy_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == name

    update = await auth_client.put(
        f"/api/v1/strategies/{strategy_id}",
        json={"description": "Updated description"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["description"] == "Updated description"

    versions = await auth_client.get(f"/api/v1/strategies/{strategy_id}/versions")
    assert versions.status_code == 200
    assert versions.json()["data"]["total_count"] >= 1
    version_id = versions.json()["data"]["items"][0]["id"]

    version_detail = await auth_client.get(
        f"/api/v1/strategies/{strategy_id}/versions/{version_id}"
    )
    assert version_detail.status_code == 200
    assert "sma_crossover" in version_detail.json()["data"]["source_code"]

    validate = await auth_client.post(
        f"/api/v1/strategies/{strategy_id}/versions/{version_id}/validate"
    )
    assert validate.status_code == 200
    assert validate.json()["data"]["status"] == "validated"
    assert validate.json()["data"]["errors"] == []
    assert len(validate.json()["data"]["compiled_hash"]) == 64

    indicators = await auth_client.get("/api/v1/indicators")
    assert indicators.status_code == 200
    names = {i["name"] for i in indicators.json()["data"]["items"]}
    assert {"sma", "ema", "rsi", "macd", "bollinger"}.issubset(names)

    delete = await auth_client.delete(f"/api/v1/strategies/{strategy_id}")
    assert delete.status_code == 204
