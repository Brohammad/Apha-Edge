"""Build return series from market bars for risk computation."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.market_data.infrastructure.models import BarModel
from alphaedge.modules.portfolio.domain.entities import Holding


class ReturnSeriesBuilder:
    @staticmethod
    async def portfolio_returns(
        session: AsyncSession,
        holdings: list[Holding],
        *,
        lookback_days: int = 252,
    ) -> tuple[list[float], list[float], list[float]]:
        """Weighted portfolio returns and equal-weight benchmark proxy."""
        if not holdings:
            return [], [], []

        all_returns: list[list[float]] = []
        for h in holdings:
            stmt = (
                select(BarModel)
                .where(
                    BarModel.instrument_id == h.instrument_id,
                    BarModel.timeframe == "1d",
                )
                .order_by(BarModel.timestamp.desc())
                .limit(lookback_days + 1)
            )
            result = await session.execute(stmt)
            bars = list(reversed(result.scalars().all()))
            if len(bars) < 2:
                continue
            rets = []
            for i in range(1, len(bars)):
                prev = float(bars[i - 1].close)
                curr = float(bars[i].close)
                rets.append((curr - prev) / prev if prev else 0.0)
            all_returns.append(rets)

        if not all_returns:
            return [], [], []

        min_len = min(len(r) for r in all_returns)
        trimmed = [r[-min_len:] for r in all_returns]
        weights = [float(h.market_value) for h in holdings[: len(trimmed)]]
        total_w = sum(weights) or 1.0
        weights = [w / total_w for w in weights]

        portfolio_rets: list[float] = []
        benchmark_rets: list[float] = []
        equity: list[float] = [1.0]
        for i in range(min_len):
            pr = sum(w * trimmed[j][i] for j, w in enumerate(weights))
            br = sum(trimmed[j][i] for j in range(len(trimmed))) / len(trimmed)
            portfolio_rets.append(pr)
            benchmark_rets.append(br)
            equity.append(equity[-1] * (1.0 + pr))
        return portfolio_rets, benchmark_rets, equity[1:]

    @staticmethod
    async def refresh_holding_prices(session: AsyncSession, holdings: list[Holding]) -> None:
        for h in holdings:
            stmt = (
                select(BarModel.close)
                .where(
                    BarModel.instrument_id == h.instrument_id,
                    BarModel.timeframe == "1d",
                )
                .order_by(BarModel.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            price = result.scalar_one_or_none()
            if price is not None:
                h.refresh_price(Decimal(str(price)))
