from unittest.mock import AsyncMock

import pytest

from alphaedge.modules.identity.domain.entities import OAuthProvider
from alphaedge.modules.identity.infrastructure.oauth import (
    build_authorization_url,
    verify_oauth_state,
)


def test_build_google_authorization_url(monkeypatch):
    monkeypatch.setattr(
        "alphaedge.modules.identity.infrastructure.oauth.settings.google_oauth_client_id",
        "test-client-id",
    )
    monkeypatch.setattr(
        "alphaedge.modules.identity.infrastructure.oauth.settings.oauth_redirect_base_url",
        "http://localhost:8000/api/v1/auth/oauth",
    )
    url, state = build_authorization_url(OAuthProvider.GOOGLE)
    assert "accounts.google.com" in url
    assert "test-client-id" in url
    assert len(state) > 10


@pytest.mark.asyncio
async def test_verify_oauth_state(monkeypatch):
    stored: dict[str, str] = {}

    class FakeRedis:
        async def get(self, key: str):
            return stored.get(key)

        async def delete(self, key: str):
            stored.pop(key, None)

        async def setex(self, key: str, ttl: int, value: str):
            stored[key] = value

    monkeypatch.setattr(
        "alphaedge.modules.identity.infrastructure.oauth.get_redis",
        AsyncMock(return_value=FakeRedis()),
    )

    from alphaedge.modules.identity.infrastructure.oauth import store_oauth_state

    await store_oauth_state("abc123")
    assert await verify_oauth_state("abc123") is True
    assert await verify_oauth_state("abc123") is False


@pytest.mark.asyncio
async def test_exchange_github_code(monkeypatch):
    import httpx

    class FakeResponse:
        def __init__(self, data: dict, status_code: int = 200):
            self._data = data
            self.status_code = status_code

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return FakeResponse({"access_token": "gh-token"})

        async def get(self, url, **kwargs):
            if url.endswith("/user"):
                return FakeResponse(
                    {"id": 42, "email": "dev@alphaedge.io", "login": "dev", "name": "Dev"}
                )
            return FakeResponse([])

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FakeClient())
    monkeypatch.setattr(
        "alphaedge.modules.identity.infrastructure.oauth.settings.github_oauth_client_id",
        "id",
    )
    monkeypatch.setattr(
        "alphaedge.modules.identity.infrastructure.oauth.settings.github_oauth_client_secret",
        "secret",
    )

    from alphaedge.modules.identity.infrastructure.oauth import _exchange_github

    info = await _exchange_github("code123")
    assert info.provider_uid == "42"
    assert info.email == "dev@alphaedge.io"
