"""HTTP-only authentication cookies."""

from __future__ import annotations

from fastapi import Request, Response

from alphaedge.config import settings

ACCESS_COOKIE = "alphaedge_access"
REFRESH_COOKIE = "alphaedge_refresh"
_COOKIE_PATH = "/api/v1"


def set_access_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path=_COOKIE_PATH,
    )


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path=f"{_COOKIE_PATH}/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE, path=_COOKIE_PATH)
    response.delete_cookie(key=REFRESH_COOKIE, path=f"{_COOKIE_PATH}/auth")


def clear_refresh_cookie(response: Response) -> None:
    clear_auth_cookies(response)


def read_access_token(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_COOKIE)
    return token.strip() if token else None


def read_refresh_token(request: Request, body_token: str | None = None) -> str | None:
    cookie_token = request.cookies.get(REFRESH_COOKIE)
    if cookie_token:
        return cookie_token
    if body_token and body_token.strip():
        return body_token.strip()
    return None
