from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from alphaedge.config import settings
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.providers import MarketDataProvider
from alphaedge.modules.market_data.domain.services import RawBar
from alphaedge.shared.domain.exceptions import ValidationError


class MockMarketDataProvider(MarketDataProvider):
    @property
    def name(self) -> str:
        return "mock"

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[RawBar]:
        bars: list[RawBar] = []
        step = self._step_for_timeframe(timeframe)
        price = Decimal("150.00")
        current = start
        while current < end:
            noise = Decimal(str((current.day % 7) * 0.5))
            o = price + noise
            h = o + Decimal("2.5")
            low = o - Decimal("1.5")
            c = o + Decimal("0.75")
            bars.append(
                RawBar(
                    symbol=symbol,
                    timestamp=current,
                    open=o,
                    high=h,
                    low=low,
                    close=c,
                    volume=Decimal("1000000") + Decimal(current.day * 10000),
                    vwap=(o + c) / 2,
                )
            )
            price = c
            current += step
        return bars

    @staticmethod
    def _step_for_timeframe(timeframe: Timeframe) -> timedelta:
        mapping = {
            Timeframe.M1: timedelta(minutes=1),
            Timeframe.M5: timedelta(minutes=5),
            Timeframe.M15: timedelta(minutes=15),
            Timeframe.H1: timedelta(hours=1),
            Timeframe.D1: timedelta(days=1),
        }
        return mapping[timeframe]


class AlphaVantageProvider(MarketDataProvider):
    BASE_URL = "https://www.alphavantage.co/query"

    @property
    def name(self) -> str:
        return "alpha_vantage"

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[RawBar]:
        if not settings.alpha_vantage_api_key:
            raise ValidationError("ALPHA_VANTAGE_API_KEY is not configured")

        if timeframe != Timeframe.D1:
            raise ValidationError("Alpha Vantage free tier supports daily bars only")

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": settings.alpha_vantage_api_key,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        if "Error Message" in payload:
            raise ValidationError(payload["Error Message"])
        if "Note" in payload:
            raise ValidationError(f"Alpha Vantage rate limit: {payload['Note']}")

        series = payload.get("Time Series (Daily)", {})
        bars: list[RawBar] = []
        for date_str, values in series.items():
            ts = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            if ts < start or ts > end:
                continue
            bars.append(
                RawBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=Decimal(values["1. open"]),
                    high=Decimal(values["2. high"]),
                    low=Decimal(values["3. low"]),
                    close=Decimal(values["4. close"]),
                    volume=Decimal(values["5. volume"]),
                )
            )
        bars.sort(key=lambda b: b.timestamp)
        return bars


def get_provider(name: str) -> MarketDataProvider:
    providers: dict[str, MarketDataProvider] = {
        "mock": MockMarketDataProvider(),
        "alpha_vantage": AlphaVantageProvider(),
    }
    provider = providers.get(name)
    if not provider:
        raise ValidationError(f"Unknown provider: {name}")
    return provider
