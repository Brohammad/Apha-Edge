from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from alphaedge.main import app

pytestmark = pytest.mark.integration


async def _second_auth_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    email = f"buyer_{uuid4().hex[:8]}@alphaedge.io"
    await ac.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123", "display_name": "Buyer"},
    )
    login = await ac.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    token = login.json()["data"]["access_token"]
    ac.headers["Authorization"] = f"Bearer {token}"
    return ac


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


@pytest.mark.asyncio
async def test_paid_listing_requires_purchase(auth_client: AsyncClient, require_migrated_db):
    org = await auth_client.post(
        "/api/v1/organizations",
        json={"name": "Paid Org", "slug": f"paid-org-{uuid4().hex[:8]}"},
    )
    org_id = org.json()["data"]["id"]

    strategy = await auth_client.post(
        "/api/v1/strategies",
        json={
            "name": "Premium Alpha",
            "strategy_type": "dsl",
            "source_code": "name: paid\nsignals: []\n",
        },
    )
    strategy_id = strategy.json()["data"]["id"]

    publish = await auth_client.post(
        "/api/v1/marketplace/listings",
        json={
            "strategy_id": strategy_id,
            "organization_id": org_id,
            "title": "Premium Strategy",
            "price_cents": 999,
        },
    )
    listing_id = publish.json()["data"]["id"]

    buyer = await _second_auth_client()
    try:
        blocked = await buyer.post(f"/api/v1/marketplace/listings/{listing_id}/clone")
        assert blocked.status_code in (400, 422)

        checkout = await buyer.post(
            f"/api/v1/payments/marketplace/listings/{listing_id}/checkout"
        )
        assert checkout.status_code == 200
        session_id = checkout.json()["data"]["session_id"]
        assert session_id.startswith("mock_")

        complete = await buyer.post(
            "/api/v1/payments/mock/complete",
            json={"session_id": session_id},
        )
        assert complete.status_code == 200

        clone = await buyer.post(f"/api/v1/marketplace/listings/{listing_id}/clone")
        assert clone.status_code == 201
    finally:
        await buyer.aclose()
