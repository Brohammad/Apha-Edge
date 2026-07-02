"""Shared helpers for integration tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.services import BarNormalizer
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyBarRepository
from alphaedge.modules.market_data.infrastructure.providers import MockMarketDataProvider
from alphaedge.shared.infrastructure.database import async_session_factory


async def seed_mock_bars(instrument_id: UUID, symbol: str, *, days: int = 90) -> int:
    """Insert mock OHLCV bars for an instrument."""
    provider = MockMarketDataProvider()
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    raw_bars = await provider.fetch_bars(symbol, Timeframe.D1, start, end)
    async with async_session_factory() as session:
        repo = SQLAlchemyBarRepository(session)
        bars = [
            BarNormalizer.to_domain(raw, instrument_id, Timeframe.D1, "mock") for raw in raw_bars
        ]
        count = await repo.upsert_many(bars)
        await session.commit()
        return count
