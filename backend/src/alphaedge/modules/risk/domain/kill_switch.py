"""Platform kill switch — Redis-backed so all API/worker processes share state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import redis
import structlog

from alphaedge.config import settings

logger = structlog.get_logger(__name__)

_REDIS_KEY = "alphaedge:risk:kill_switch"


@dataclass
class KillSwitchState:
    enabled: bool = False
    reason: str = ""
    triggered_at: datetime | None = None
    triggered_by: str | None = None


def _sync_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _parse(raw: str | None) -> KillSwitchState:
    if not raw:
        return KillSwitchState()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return KillSwitchState()
    triggered_at = None
    if data.get("triggered_at"):
        triggered_at = datetime.fromisoformat(data["triggered_at"])
    return KillSwitchState(
        enabled=bool(data.get("enabled")),
        reason=str(data.get("reason") or ""),
        triggered_at=triggered_at,
        triggered_by=data.get("triggered_by"),
    )


def _serialize(state: KillSwitchState) -> str:
    return json.dumps(
        {
            "enabled": state.enabled,
            "reason": state.reason,
            "triggered_at": state.triggered_at.isoformat() if state.triggered_at else None,
            "triggered_by": state.triggered_by,
        }
    )


def get_kill_switch() -> KillSwitchState:
    try:
        client = _sync_redis()
        return _parse(client.get(_REDIS_KEY))
    except redis.RedisError as exc:
        logger.warning("kill_switch_redis_unavailable", error=str(exc))
        # Fail closed in production: if we cannot read kill-switch state, block orders.
        if settings.is_production:
            return KillSwitchState(
                enabled=True,
                reason="Kill switch state unavailable (Redis error) — failing closed",
                triggered_by="system",
                triggered_at=datetime.now(UTC),
            )
        return KillSwitchState()


def activate_kill_switch(reason: str, *, actor: str = "system") -> KillSwitchState:
    state = KillSwitchState(
        enabled=True,
        reason=reason.strip() or "Platform halt",
        triggered_at=datetime.now(UTC),
        triggered_by=actor,
    )
    try:
        client = _sync_redis()
        client.set(_REDIS_KEY, _serialize(state))
    except redis.RedisError as exc:
        logger.error("kill_switch_activate_failed", error=str(exc))
        raise
    logger.warning(
        "kill_switch_activated",
        reason=state.reason,
        actor=actor,
    )
    return state


def deactivate_kill_switch(*, actor: str = "system") -> KillSwitchState:
    state = KillSwitchState()
    try:
        client = _sync_redis()
        client.set(_REDIS_KEY, _serialize(state))
    except redis.RedisError as exc:
        logger.error("kill_switch_deactivate_failed", error=str(exc))
        raise
    logger.info("kill_switch_deactivated", actor=actor)
    return state


def exposure_summary(*, gross: Decimal, net: Decimal, equity: Decimal) -> dict[str, str]:
    return {
        "gross_exposure": str(gross),
        "net_exposure": str(net),
        "equity": str(equity),
        "gross_leverage": str(gross / equity) if equity > 0 else "0",
    }
