"""Live quote lookup with provider + database fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from alphaedge.config import settings
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.repositories import BarRepository, InstrumentRepository
from alphaedge.shared.domain.exceptions import ValidationError

QUOTE_CACHE_TTL = 300  # 5 min — respects Alpha Vantage rate limits


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    price: Decimal
    change_pct: Decimal | None
    as_of: datetime
    source: str


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
        )

    async def set(self, quote: QuoteSnapshot) -> None:
        import json

        payload = {
            "symbol": quote.symbol,
            "price": str(quote.price),
            "change_pct": str(quote.change_pct) if quote.change_pct is not None else None,
            "as_of": quote.as_of.isoformat(),
            "source": quote.source,
        }
        await self._redis.set(self._key(quote.symbol), json.dumps(payload), ex=QUOTE_CACHE_TTL)


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
        self._live_client = AlphaVantageQuoteClient()

    async def get_quotes(self, symbols: list[str]) -> list[QuoteSnapshot]:
        results: list[QuoteSnapshot] = []
        for symbol in symbols:
            quote = await self._get_one(symbol)
            if quote:
                results.append(quote)
        return results

    async def _get_one(self, symbol: str) -> QuoteSnapshot | None:
        sym = symbol.upper()
        if self._cache:
            cached = await self._cache.get(sym)
            if cached:
                return cached

        try:
            quote = await self._live_client.fetch(sym)
            if self._cache:
                await self._cache.set(quote)
            return quote
        except ValidationError:
            pass

        return await self._from_database(sym)

    async def _from_database(self, symbol: str) -> QuoteSnapshot | None:
        instrument = await self._instrument_repo.get_by_symbol(symbol)
        if not instrument:
            return None

        bars = await self._bar_repo.get_bars(
            instrument.id,
            Timeframe.D1,
            start=None,
            end=None,
            limit=2,
            offset=0,
        )
        if not bars:
            return None

        latest = bars[0]
        prev = bars[1] if len(bars) > 1 else None
        change_pct = None
        if prev and prev.close != 0:
            change_pct = (latest.close - prev.close) / prev.close * Decimal("100")

        return QuoteSnapshot(
            symbol=symbol,
            price=latest.close,
            change_pct=change_pct,
            as_of=latest.timestamp,
            source=latest.source,
        )
