from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.services import BarNormalizer, BarValidator, RawBar
from alphaedge.modules.market_data.infrastructure.providers import (
    MockMarketDataProvider,
    PolygonProvider,
    get_provider,
)
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


class TestProviderRegistry:
    def test_get_polygon_provider(self):
        provider = get_provider("polygon")
        assert provider.name == "polygon"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValidationError):
            get_provider("unknown")


@pytest.mark.asyncio
class TestPolygonProvider:
    async def test_fetch_bars_requires_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "alphaedge.modules.market_data.infrastructure.providers.settings.polygon_api_key",
            "",
        )
        provider = PolygonProvider()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 5, tzinfo=UTC)
        with pytest.raises(ValidationError, match="POLYGON_API_KEY"):
            await provider.fetch_bars("AAPL", Timeframe.D1, start, end)

    async def test_fetch_bars_parses_response(self, monkeypatch):
        monkeypatch.setattr(
            "alphaedge.modules.market_data.infrastructure.providers.settings.polygon_api_key",
            "test-key",
        )
        provider = PolygonProvider()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 5, tzinfo=UTC)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "o": 100.0,
                    "h": 105.0,
                    "l": 99.0,
                    "c": 103.0,
                    "v": 1000000,
                    "vw": 101.5,
                    "t": int(datetime(2026, 1, 2, tzinfo=UTC).timestamp() * 1000),
                }
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "alphaedge.modules.market_data.infrastructure.providers.httpx.AsyncClient",
            return_value=mock_client,
        ):
            bars = await provider.fetch_bars("AAPL", Timeframe.D1, start, end)

        assert len(bars) == 1
        assert bars[0].symbol == "AAPL"
        assert bars[0].close == Decimal("103.0")
        assert bars[0].vwap == Decimal("101.5")
