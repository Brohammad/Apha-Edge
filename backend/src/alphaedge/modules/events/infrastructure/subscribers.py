"""Domain event subscribers registry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from alphaedge.shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]

_SUBSCRIBERS: dict[str, list[EventHandler]] = {}


def subscribe(event_type: str, handler: EventHandler) -> None:
    _SUBSCRIBERS.setdefault(event_type, []).append(handler)


async def dispatch_event(event_type: str, payload: dict[str, Any]) -> None:
    for handler in _SUBSCRIBERS.get(event_type, []):
        await handler(payload)
    if event_type not in _SUBSCRIBERS:
        logger.info("outbox_event_no_subscriber", event_type=event_type)


async def _on_order_filled(payload: dict[str, Any]) -> None:
    logger.info("order_filled_event", order_id=payload.get("order_id"))


async def _on_risk_breach(payload: dict[str, Any]) -> None:
    logger.info("risk_breach_event", portfolio_id=payload.get("portfolio_id"))


subscribe("order.filled", _on_order_filled)
subscribe("risk.breach", _on_risk_breach)
