"""Per-email login brute-force protection using Redis."""

from __future__ import annotations

from alphaedge.config import settings
from alphaedge.shared.domain.exceptions import AuthenticationError
from alphaedge.shared.infrastructure.redis import get_redis

_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 900
_KEY_PREFIX = "login_fail:"


async def check_login_allowed(email: str) -> None:
    if settings.is_testing:
        return
    redis = await get_redis()
    count_raw = await redis.get(f"{_KEY_PREFIX}{email.lower()}")
    if count_raw is None:
        return
    count = int(count_raw.decode() if isinstance(count_raw, bytes) else count_raw)
    if count >= _MAX_FAILURES:
        raise AuthenticationError(
            "Too many failed login attempts. Try again later."
        )


async def record_login_failure(email: str) -> None:
    if settings.is_testing:
        return
    redis = await get_redis()
    key = f"{_KEY_PREFIX}{email.lower()}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _LOCKOUT_SECONDS)


async def clear_login_failures(email: str) -> None:
    if settings.is_testing:
        return
    redis = await get_redis()
    await redis.delete(f"{_KEY_PREFIX}{email.lower()}")
