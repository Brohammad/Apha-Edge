"""Redis cache for latest portfolio risk snapshots."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.config import settings
from alphaedge.modules.risk.domain.entities import RiskSnapshot
from alphaedge.shared.infrastructure.redis import get_redis


def _cache_key(portfolio_id: UUID) -> str:
    return f"risk:snapshot:latest:{portfolio_id}"


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


async def get_cached_snapshot(portfolio_id: UUID) -> RiskSnapshot | None:
    redis = await get_redis()
    raw = await redis.get(_cache_key(portfolio_id))
    if not raw:
        return None
    data = json.loads(raw)
    return RiskSnapshot(
        id=UUID(data["id"]),
        portfolio_id=UUID(data["portfolio_id"]),
        snapshot_at=datetime.fromisoformat(data["snapshot_at"]),
        var_95=_decimal_or_none(data.get("var_95")),
        var_99=_decimal_or_none(data.get("var_99")),
        max_drawdown=_decimal_or_none(data.get("max_drawdown")),
        sharpe_ratio=_decimal_or_none(data.get("sharpe_ratio")),
        sortino_ratio=_decimal_or_none(data.get("sortino_ratio")),
        beta=_decimal_or_none(data.get("beta")),
        alpha=_decimal_or_none(data.get("alpha")),
        volatility=_decimal_or_none(data.get("volatility")),
        correlation_matrix=data.get("correlation_matrix"),
        metrics=data.get("metrics", {}),
    )


async def set_cached_snapshot(snapshot: RiskSnapshot) -> None:
    redis = await get_redis()
    payload = {
        "id": str(snapshot.id),
        "portfolio_id": str(snapshot.portfolio_id),
        "snapshot_at": snapshot.snapshot_at.isoformat(),
        "var_95": str(snapshot.var_95) if snapshot.var_95 is not None else None,
        "var_99": str(snapshot.var_99) if snapshot.var_99 is not None else None,
        "max_drawdown": str(snapshot.max_drawdown) if snapshot.max_drawdown is not None else None,
        "sharpe_ratio": str(snapshot.sharpe_ratio) if snapshot.sharpe_ratio is not None else None,
        "sortino_ratio": str(snapshot.sortino_ratio)
        if snapshot.sortino_ratio is not None
        else None,
        "beta": str(snapshot.beta) if snapshot.beta is not None else None,
        "alpha": str(snapshot.alpha) if snapshot.alpha is not None else None,
        "volatility": str(snapshot.volatility) if snapshot.volatility is not None else None,
        "correlation_matrix": snapshot.correlation_matrix,
        "metrics": snapshot.metrics,
    }
    await redis.set(
        _cache_key(snapshot.portfolio_id),
        json.dumps(payload),
        ex=settings.risk_snapshot_cache_ttl_seconds,
    )


async def invalidate_snapshot_cache(portfolio_id: UUID) -> None:
    redis = await get_redis()
    await redis.delete(_cache_key(portfolio_id))
