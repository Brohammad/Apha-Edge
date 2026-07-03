import pytest
from httpx import AsyncClient

from alphaedge.config import settings

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_and_use_api_key(auth_client: AsyncClient, require_migrated_db):
    create = await auth_client.post(
        "/api/v1/auth/api-keys",
        json={"name": "CI test key", "scopes": ["read:*"], "rate_limit_tier": "pro"},
    )
    assert create.status_code == 201
    data = create.json()["data"]
    raw_key = data["key"]
    assert raw_key.startswith("ae_live_")

    listing = await auth_client.get("/api/v1/auth/api-keys")
    assert listing.status_code == 200
    assert len(listing.json()["data"]["items"]) >= 1

    key_client = AsyncClient(
        transport=auth_client._transport,
        base_url=auth_client.base_url,
        headers={"X-API-Key": raw_key},
    )
    me = await key_client.get("/api/v1/auth/me")
    assert me.status_code == 200

    key_id = data["api_key"]["id"]
    revoke = await auth_client.delete(f"/api/v1/auth/api-keys/{key_id}")
    assert revoke.status_code == 204


@pytest.mark.asyncio
async def test_rate_limit_headers(auth_client: AsyncClient, require_migrated_db):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    if settings.rate_limit_enabled:
        assert "X-RateLimit-Limit" in resp.headers


@pytest.mark.asyncio
async def test_oauth_start_redirects_when_configured(auth_client: AsyncClient, require_migrated_db):
    if not settings.google_oauth_client_id:
        pytest.skip("Google OAuth not configured")
    resp = await auth_client.get("/api/v1/auth/oauth/google", follow_redirects=False)
    assert resp.status_code in (307, 302)
    assert "accounts.google.com" in resp.headers.get("location", "")
