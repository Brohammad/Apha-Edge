"""Indian market historical bar provider (mock skeleton for NSE/BSE symbols)."""

from datetime import timedelta
from decimal import Decimal

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.providers import MarketDataProvider
from alphaedge.modules.market_data.domain.services import RawBar
from alphaedge.modules.market_data.infrastructure.providers import step_for_timeframe

# Base INR prices for seeded Indian symbols.
_INR_BASE_PRICES: dict[str, Decimal] = {
    "RELIANCE": Decimal("2850"),
    "TCS": Decimal("4100"),
    "INFY": Decimal("1850"),
    "HDFCBANK": Decimal("1650"),
    "SBIN": Decimal("820"),
}


class IndianMarketDataProvider(MarketDataProvider):
    """Generates synthetic INR bars for Indian equities when live feeds are unavailable."""

    @property
    def name(self) -> str:
        return "indian"

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start,
        end,
    ) -> list[RawBar]:
        base = _INR_BASE_PRICES.get(symbol.upper(), Decimal("1000"))
        step = step_for_timeframe(timeframe)
        bars: list[RawBar] = []
        price = base
        current = start
        while current < end:
            noise = Decimal(str((current.day % 5) * 2))
            o = price + noise
            h = o + Decimal("15")
            low = o - Decimal("10")
            c = o + Decimal("5")
            bars.append(
                RawBar(
                    symbol=symbol,
                    timestamp=current,
                    open=o,
                    high=h,
                    low=low,
                    close=c,
                    volume=Decimal("500000") + Decimal(current.day * 5000),
                    vwap=(o + c) / 2,
                )
            )
            price = c
            current += step
        return bars
