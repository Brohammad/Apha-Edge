"""Live quote lookup with provider chain + database fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

import httpx

from alphaedge.config import settings
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.repositories import BarRepository, InstrumentRepository
from alphaedge.shared.domain.exceptions import ValidationError

QUOTE_CACHE_TTL = 900  # 15 min
LIVE_QUOTE_SOURCES = frozenset({"polygon", "alpha_vantage"})


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    price: Decimal
    change_pct: Decimal | None
    as_of: datetime
    source: str
    fallback_reason: str | None = None


class QuoteClient(Protocol):
    async def fetch(self, symbol: str) -> QuoteSnapshot: ...


class PolygonQuoteClient:
    """Uses Polygon daily aggregates (free tier — previous close, not real-time snapshot)."""

    BASE_URL = "https://api.polygon.io"

    async def fetch(self, symbol: str) -> QuoteSnapshot:
        if not settings.polygon_api_key:
            raise ValidationError("POLYGON_API_KEY is not configured")

        sym = symbol.upper()
        end = datetime.now(UTC).date()
        start = end - timedelta(days=14)
        url = f"{self.BASE_URL}/v2/aggs/ticker/{sym}/range/1/day/{start}/{end}"
        params = {
            "adjusted": "true",
            "sort": "desc",
            "limit": 2,
            "apiKey": settings.polygon_api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        status = payload.get("status")
        if status not in (None, "OK", "DELAYED"):
            raise ValidationError(
                str(payload.get("message", payload.get("error", "Polygon API error")))
            )

        results = payload.get("results") or []
        if not results:
            raise ValidationError(f"No Polygon quote data for {sym}")

        latest = results[0]
        price = Decimal(str(latest["c"]))
        as_of = datetime.fromtimestamp(latest["t"] / 1000, tz=UTC)
        change_pct = None
        if len(results) > 1:
            prev_close = Decimal(str(results[1]["c"]))
            if prev_close != 0:
                change_pct = (price - prev_close) / prev_close * Decimal("100")

        return QuoteSnapshot(
            symbol=sym,
            price=price,
            change_pct=change_pct,
            as_of=as_of,
            source="polygon",
        )


class AlphaVantageQuoteClient:
    BASE_URL = "https://www.alphavantage.co/query"

    async def fetch(self, symbol: str) -> QuoteSnapshot:
        if not settings.alpha_vantage_api_key:
            raise ValidationError("ALPHA_VANTAGE_API_KEY is not configured")

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": settings.alpha_vantage_api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        if "Error Message" in payload:
            raise ValidationError(payload["Error Message"])
        if "Note" in payload:
            raise ValidationError(f"Alpha Vantage rate limit: {payload['Note']}")
        if "Information" in payload:
            raise ValidationError(payload["Information"])

        quote = payload.get("Global Quote") or {}
        price_raw = quote.get("05. price")
        if not price_raw:
            raise ValidationError(f"No quote data for {symbol}")

        change_pct_raw = quote.get("10. change percent", "0%").rstrip("%")
        return QuoteSnapshot(
            symbol=symbol.upper(),
            price=Decimal(price_raw),
            change_pct=Decimal(change_pct_raw),
            as_of=datetime.now(UTC),
            source="alpha_vantage",
        )


class QuoteCache:
    def __init__(self, redis_client: object) -> None:
        self._redis = redis_client

    def _key(self, symbol: str) -> str:
        return f"quote:latest:{symbol.upper()}"

    async def get(self, symbol: str) -> QuoteSnapshot | None:
        import json

        raw = await self._redis.get(self._key(symbol))
        if not raw:
            return None
        data = json.loads(raw)
        return QuoteSnapshot(
            symbol=data["symbol"],
            price=Decimal(data["price"]),
            change_pct=Decimal(data["change_pct"]) if data.get("change_pct") is not None else None,
            as_of=datetime.fromisoformat(data["as_of"]),
            source=data["source"],
            fallback_reason=data.get("fallback_reason"),
        )

    async def set(self, quote: QuoteSnapshot) -> None:
        import json

        payload = {
            "symbol": quote.symbol,
            "price": str(quote.price),
            "change_pct": str(quote.change_pct) if quote.change_pct is not None else None,
            "as_of": quote.as_of.isoformat(),
            "source": quote.source,
            "fallback_reason": quote.fallback_reason,
        }
        await self._redis.set(self._key(quote.symbol), json.dumps(payload), ex=QUOTE_CACHE_TTL)


def _quote_clients() -> list[QuoteClient]:
    provider = settings.quote_provider
    polygon = PolygonQuoteClient()
    alpha_vantage = AlphaVantageQuoteClient()

    if provider == "polygon":
        return [polygon]
    if provider == "alpha_vantage":
        return [alpha_vantage]

    # auto: prefer Polygon (higher free limits), then Alpha Vantage
    clients: list[QuoteClient] = []
    if settings.polygon_api_key:
        clients.append(polygon)
    if settings.alpha_vantage_api_key:
        clients.append(alpha_vantage)
    return clients


class QuoteService:
    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        bar_repo: BarRepository,
        cache: QuoteCache | None = None,
    ) -> None:
        self._instrument_repo = instrument_repo
        self._bar_repo = bar_repo
        self._cache = cache

    async def get_quotes(self, symbols: list[str]) -> list[QuoteSnapshot]:
        results: list[QuoteSnapshot] = []
        seen: set[str] = set()
        for symbol in symbols:
            sym = symbol.upper()
            if sym in seen:
                continue
            seen.add(sym)
            quote = await self._get_one(sym)
            if quote:
                results.append(quote)
        return results

    async def _get_one(self, symbol: str) -> QuoteSnapshot | None:
        sym = symbol.upper()
        if self._cache:
            cached = await self._cache.get(sym)
            if cached and cached.source in LIVE_QUOTE_SOURCES and not cached.fallback_reason:
                return cached

        errors: list[str] = []
        for client in _quote_clients():
            try:
                quote = await client.fetch(sym)
                if self._cache:
                    await self._cache.set(quote)
                return quote
            except ValidationError as exc:
                errors.append(str(exc))

        db_quote = await self._from_database(sym)
        if db_quote:
            reason = "; ".join(errors) if errors else "No live quote provider configured"
            return QuoteSnapshot(
                symbol=db_quote.symbol,
                price=db_quote.price,
                change_pct=db_quote.change_pct,
                as_of=db_quote.as_of,
                source="database",
                fallback_reason=reason,
            )
        return None

    async def _from_database(self, symbol: str) -> QuoteSnapshot | None:
        instrument = await self._instrument_repo.get_by_symbol(symbol)
        if not instrument:
            return None

        latest = await self._bar_repo.get_latest(instrument.id, Timeframe.D1)
        if not latest:
            return None

        bars = await self._bar_repo.get_bars(
            instrument.id,
            Timeframe.D1,
            start=None,
            end=None,
            limit=2,
            offset=0,
        )
        prev = bars[1] if len(bars) > 1 else None
        change_pct = None
        if prev and prev.close != 0:
            change_pct = (latest.close - prev.close) / prev.close * Decimal("100")

        return QuoteSnapshot(
            symbol=symbol,
            price=latest.close,
            change_pct=change_pct,
            as_of=latest.timestamp,
            source="database",
        )
