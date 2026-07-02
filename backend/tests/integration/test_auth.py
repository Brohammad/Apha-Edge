import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_register_login_and_me(auth_client: AsyncClient, require_migrated_db):
    me = await auth_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["email"].endswith("@alphaedge.io")
    assert me.json()["data"]["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, require_migrated_db):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@alphaedge.io", "password": "wrongpassword"},
    )
    assert response.status_code == 401
