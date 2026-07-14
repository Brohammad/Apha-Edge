"""Unit tests for risk snapshot Redis cache."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from alphaedge.modules.risk.domain.entities import RiskSnapshot
from alphaedge.modules.risk.infrastructure.snapshot_cache import (
    get_cached_snapshot,
    set_cached_snapshot,
)


@pytest.mark.asyncio
async def test_snapshot_cache_round_trip():
    portfolio_id = uuid4()
    snapshot = RiskSnapshot.create(
        portfolio_id,
        var_95=Decimal("0.05"),
        sharpe_ratio=Decimal("1.2"),
        metrics={"violations": []},
    )
    snapshot.snapshot_at = datetime.now(UTC)

    mock_redis = AsyncMock()
    stored: dict[str, str] = {}

    async def fake_set(key: str, value: str, ex: int | None = None) -> None:
        stored[key] = value

    async def fake_get(key: str) -> str | None:
        return stored.get(key)

    mock_redis.set = fake_set
    mock_redis.get = fake_get

    with patch(
        "alphaedge.modules.risk.infrastructure.snapshot_cache.get_redis",
        AsyncMock(return_value=mock_redis),
    ):
        await set_cached_snapshot(snapshot)
        cached = await get_cached_snapshot(portfolio_id)

    assert cached is not None
    assert cached.portfolio_id == portfolio_id
    assert cached.var_95 == Decimal("0.05")
    assert cached.sharpe_ratio == Decimal("1.2")
