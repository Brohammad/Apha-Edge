import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from alphaedge.config import settings
from alphaedge.modules.identity.domain.entities import OAuthProvider
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.infrastructure.redis import get_redis

OAUTH_STATE_TTL = 600


@dataclass(frozen=True)
class OAuthUserInfo:
    provider_uid: str
    email: str
    display_name: str


def _redirect_uri(provider: OAuthProvider) -> str:
    return f"{settings.oauth_redirect_base_url}/{provider.value}/callback"


async def store_oauth_state(state: str) -> None:
    redis = await get_redis()
    await redis.setex(f"oauth:state:{state}", OAUTH_STATE_TTL, "1")


async def verify_oauth_state(state: str) -> bool:
    redis = await get_redis()
    key = f"oauth:state:{state}"
    exists = await redis.get(key)
    if exists:
        await redis.delete(key)
        return True
    return False


def build_authorization_url(provider: OAuthProvider) -> tuple[str, str]:
    state = secrets.token_urlsafe(24)
    if provider == OAuthProvider.GOOGLE:
        if not settings.google_oauth_client_id:
            raise ValidationError("Google OAuth is not configured")
        params = {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": _redirect_uri(provider),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return url, state

    if provider == OAuthProvider.GITHUB:
        if not settings.github_oauth_client_id:
            raise ValidationError("GitHub OAuth is not configured")
        params = {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": _redirect_uri(provider),
            "scope": "read:user user:email",
            "state": state,
        }
        url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        return url, state

    raise ValidationError(f"Unsupported OAuth provider: {provider.value}")


async def exchange_code(provider: OAuthProvider, code: str) -> OAuthUserInfo:
    if provider == OAuthProvider.GOOGLE:
        return await _exchange_google(code)
    if provider == OAuthProvider.GITHUB:
        return await _exchange_github(code)
    raise ValidationError(f"Unsupported OAuth provider: {provider.value}")


async def _exchange_google(code: str) -> OAuthUserInfo:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": _redirect_uri(OAuthProvider.GOOGLE),
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        data = user_resp.json()

    email = data.get("email", "")
    if not email:
        raise ValidationError("Google account did not return an email address")
    return OAuthUserInfo(
        provider_uid=str(data["id"]),
        email=email.lower(),
        display_name=data.get("name") or email.split("@")[0],
    )


async def _exchange_github(code: str) -> OAuthUserInfo:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "code": code,
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "redirect_uri": _redirect_uri(OAuthProvider.GITHUB),
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_resp.raise_for_status()
        data = user_resp.json()

        email = data.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
            email = primary["email"] if primary else None

    if not email:
        raise ValidationError("GitHub account did not return an email address")
    return OAuthUserInfo(
        provider_uid=str(data["id"]),
        email=email.lower(),
        display_name=data.get("name") or data.get("login") or email.split("@")[0],
    )
