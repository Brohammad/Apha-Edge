from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.services import BarNormalizer, BarValidator, RawBar
from alphaedge.modules.market_data.infrastructure.providers import MockMarketDataProvider
from alphaedge.shared.domain.exceptions import ValidationError


class TestBarValidator:
    def test_valid_bar(self):
        raw = RawBar(
            symbol="AAPL",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("103"),
            volume=Decimal("1000000"),
        )
        assert BarValidator.validate(raw).symbol == "AAPL"

    def test_high_less_than_low_raises(self):
        raw = RawBar(
            symbol="AAPL",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("90"),
            low=Decimal("99"),
            close=Decimal("95"),
            volume=Decimal("1000"),
        )
        with pytest.raises(ValidationError):
            BarValidator.validate(raw)

    def test_naive_timestamp_raises(self):
        raw = RawBar(
            symbol="AAPL",
            timestamp=datetime(2026, 1, 1),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("103"),
            volume=Decimal("1000"),
        )
        with pytest.raises(ValidationError):
            BarValidator.validate(raw)


class TestBarNormalizer:
    def test_to_domain(self):
        instrument_id = uuid4()
        raw = RawBar(
            symbol="AAPL",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("99"),
            close=Decimal("103"),
            volume=Decimal("1000000"),
        )
        bar = BarNormalizer.to_domain(raw, instrument_id, Timeframe.D1, "mock")
        assert bar.instrument_id == instrument_id
        assert bar.timeframe == Timeframe.D1
        assert bar.source == "mock"


@pytest.mark.asyncio
class TestMockProvider:
    async def test_fetch_bars(self):
        provider = MockMarketDataProvider()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 10, tzinfo=UTC)
        bars = await provider.fetch_bars("AAPL", Timeframe.D1, start, end)
        assert len(bars) == 9
        assert bars[0].symbol == "AAPL"
        assert bars[0].close > 0
