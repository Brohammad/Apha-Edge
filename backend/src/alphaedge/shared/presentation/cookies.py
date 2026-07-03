"""HTTP-only refresh token cookies."""

from __future__ import annotations

from fastapi import Request, Response

from alphaedge.config import settings

REFRESH_COOKIE = "alphaedge_refresh"
_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path=_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path=_COOKIE_PATH)


def read_refresh_token(request: Request, body_token: str | None = None) -> str | None:
    cookie_token = request.cookies.get(REFRESH_COOKIE)
    if cookie_token:
        return cookie_token
    if body_token and body_token.strip():
        return body_token.strip()
    return None
