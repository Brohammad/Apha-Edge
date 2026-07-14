from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from alphaedge.config import settings
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.providers import MarketDataProvider
from alphaedge.modules.market_data.domain.services import RawBar
from alphaedge.shared.domain.exceptions import ValidationError


def step_for_timeframe(timeframe: Timeframe) -> timedelta:
    mapping = {
        Timeframe.M1: timedelta(minutes=1),
        Timeframe.M5: timedelta(minutes=5),
        Timeframe.M15: timedelta(minutes=15),
        Timeframe.H1: timedelta(hours=1),
        Timeframe.D1: timedelta(days=1),
    }
    return mapping[timeframe]


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
        step = step_for_timeframe(timeframe)
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
        return step_for_timeframe(timeframe)


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


class PolygonProvider(MarketDataProvider):
    BASE_URL = "https://api.polygon.io"

    @property
    def name(self) -> str:
        return "polygon"

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[RawBar]:
        if not settings.polygon_api_key:
            raise ValidationError("POLYGON_API_KEY is not configured")

        multiplier, timespan = self._timeframe_params(timeframe)
        from_bound = self._format_bound(start, timeframe)
        to_bound = self._format_bound(end, timeframe)
        url = (
            f"{self.BASE_URL}/v2/aggs/ticker/{symbol.upper()}/range/"
            f"{multiplier}/{timespan}/{from_bound}/{to_bound}"
        )

        bars: list[RawBar] = []
        params: dict[str, str | int] | None = {
            "apiKey": settings.polygon_api_key,
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

                if payload.get("status") not in (None, "OK", "DELAYED"):
                    raise ValidationError(
                        payload.get("error", payload.get("message", "Polygon API error"))
                    )

                for item in payload.get("results", []):
                    ts = datetime.fromtimestamp(item["t"] / 1000, tz=UTC)
                    if ts < start or ts > end:
                        continue
                    bars.append(
                        RawBar(
                            symbol=symbol,
                            timestamp=ts,
                            open=Decimal(str(item["o"])),
                            high=Decimal(str(item["h"])),
                            low=Decimal(str(item["l"])),
                            close=Decimal(str(item["c"])),
                            volume=Decimal(str(item["v"])),
                            vwap=Decimal(str(item["vw"])) if item.get("vw") is not None else None,
                        )
                    )

                url = payload.get("next_url")
                params = {"apiKey": settings.polygon_api_key} if url else None

        bars.sort(key=lambda b: b.timestamp)
        return bars

    @staticmethod
    def _timeframe_params(timeframe: Timeframe) -> tuple[int, str]:
        mapping = {
            Timeframe.M1: (1, "minute"),
            Timeframe.M5: (5, "minute"),
            Timeframe.M15: (15, "minute"),
            Timeframe.H1: (1, "hour"),
            Timeframe.D1: (1, "day"),
        }
        return mapping[timeframe]

    @staticmethod
    def _format_bound(dt: datetime, timeframe: Timeframe) -> str:
        if timeframe == Timeframe.D1:
            return dt.strftime("%Y-%m-%d")
        return str(int(dt.timestamp() * 1000))


def get_provider(name: str) -> MarketDataProvider:
    from alphaedge.modules.market_data.infrastructure.indian_provider import (
        IndianMarketDataProvider,
    )

    providers: dict[str, MarketDataProvider] = {
        "mock": MockMarketDataProvider(),
        "alpha_vantage": AlphaVantageProvider(),
        "polygon": PolygonProvider(),
        "indian": IndianMarketDataProvider(),
    }
    provider = providers.get(name)
    if not provider:
        raise ValidationError(f"Unknown provider: {name}")
    return provider
