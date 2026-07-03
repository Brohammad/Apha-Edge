import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_organization_create_and_list(auth_client: AsyncClient, require_migrated_db):
    slug = f"alpha-desk-{uuid4().hex[:8]}"
    create = await auth_client.post(
        "/api/v1/organizations",
        json={"name": "Alpha Quant Desk", "slug": slug},
    )
    assert create.status_code == 201
    org_id = create.json()["data"]["id"]

    listing = await auth_client.get("/api/v1/organizations")
    assert listing.status_code == 200
    ids = [o["id"] for o in listing.json()["data"]["items"]]
    assert org_id in ids


@pytest.mark.asyncio
async def test_marketplace_publish_and_clone(auth_client: AsyncClient, require_migrated_db):
    org = await auth_client.post(
        "/api/v1/organizations",
        json={"name": "Market Org", "slug": f"market-org-{uuid4().hex[:8]}"},
    )
    org_id = org.json()["data"]["id"]

    strategy = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": "Listed Alpha",
            "strategy_type": "dsl",
            "source_code": "name: test\nsignals: []\n",
        },
    )
    strategy_id = strategy.json()["data"]["id"]

    publish = await auth_client.post(
        "/api/v1/marketplace/listings",
        json={
            "strategy_id": strategy_id,
            "organization_id": org_id,
            "title": "Golden Cross Pro",
            "description": "Battle-tested crossover",
            "price_cents": 0,
        },
    )
    assert publish.status_code == 201
    listing_id = publish.json()["data"]["id"]

    public = await auth_client.get("/api/v1/marketplace/listings")
    assert public.status_code == 200
    assert any(i["id"] == listing_id for i in public.json()["data"]["items"])

    clone = await auth_client.post(f"/api/v1/marketplace/listings/{listing_id}/clone")
    assert clone.status_code == 201
    assert "strategy_id" in clone.json()["data"]
