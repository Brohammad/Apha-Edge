"""Short-lived, single-use WebSocket authentication tickets (Redis-backed)."""

from __future__ import annotations

import secrets
from uuid import UUID

from alphaedge.shared.infrastructure.redis import get_redis

_TICKET_TTL_SECONDS = 60
_KEY_PREFIX = "ws_ticket:"


async def issue_ws_ticket(user_id: UUID) -> str:
    ticket = secrets.token_urlsafe(32)
    redis = await get_redis()
    await redis.setex(f"{_KEY_PREFIX}{ticket}", _TICKET_TTL_SECONDS, str(user_id))
    return ticket


async def consume_ws_ticket(ticket: str) -> UUID | None:
    if not ticket:
        return None
    redis = await get_redis()
    key = f"{_KEY_PREFIX}{ticket}"
    raw = await redis.get(key)
    if not raw:
        return None
    await redis.delete(key)
    value = raw.decode() if isinstance(raw, bytes) else str(raw)
    return UUID(value)
