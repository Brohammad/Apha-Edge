from decimal import Decimal
from uuid import UUID

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio
from alphaedge.modules.portfolio.domain.repositories import HoldingRepository


class Rebalancer:
    """Generate proposed trades to move a portfolio toward target weights."""

    @staticmethod
    def generate(
        portfolio: Portfolio,
        holdings: list[Holding],
        target_allocation: dict[str, float],
        *,
        symbol_by_instrument: dict[UUID, str],
    ) -> list[dict[str, object]]:
        total_value = portfolio.cash_balance + sum(h.market_value for h in holdings)
        if total_value <= 0:
            return []

        current_weights: dict[str, Decimal] = {}
        for h in holdings:
            symbol = symbol_by_instrument.get(h.instrument_id, str(h.instrument_id))
            current_weights[symbol] = h.market_value / total_value

        proposed: list[dict[str, object]] = []
        for symbol, target_w in target_allocation.items():
            current_w = float(current_weights.get(symbol, Decimal("0")))
            delta = target_w - current_w
            if abs(delta) < 0.001:
                continue
            side = "buy" if delta > 0 else "sell"
            notional = abs(Decimal(str(delta))) * total_value
            proposed.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "target_weight": target_w,
                    "current_weight": round(current_w, 6),
                    "notional": str(notional.quantize(Decimal("0.01"))),
                }
            )
        return proposed


class HoldingsSync:
    """Apply closed backtest trades to portfolio holdings."""

    @staticmethod
    async def apply_backtest_trades(
        portfolio: Portfolio,
        holding_repo: HoldingRepository,
        trades: list,
    ) -> list[Holding]:
        """Update holdings from backtest closed trades (buy side entries)."""
        updated: list[Holding] = []
        for trade in trades:
            if trade.exit_price is None:
                continue
            existing = await holding_repo.get_by_portfolio_and_instrument(
                portfolio.id, trade.instrument_id
            )
            if trade.side == "buy":
                if existing:
                    new_qty = existing.quantity + trade.quantity
                    if new_qty <= 0:
                        await holding_repo.delete(existing.id)
                        continue
                    total_cost = (
                        existing.avg_cost * existing.quantity + trade.entry_price * trade.quantity
                    )
                    avg = total_cost / new_qty
                    existing.quantity = new_qty
                    existing.avg_cost = avg
                    existing.refresh_price(trade.exit_price)
                    updated.append(await holding_repo.upsert(existing))
                else:
                    holding = Holding.create(
                        portfolio.id,
                        trade.instrument_id,
                        trade.quantity,
                        trade.entry_price,
                        trade.exit_price,
                    )
                    updated.append(await holding_repo.upsert(holding))
            elif existing and existing.quantity > 0:
                new_qty = existing.quantity - trade.quantity
                if new_qty <= 0:
                    await holding_repo.delete(existing.id)
                else:
                    existing.quantity = new_qty
                    existing.refresh_price(trade.exit_price)
                    updated.append(await holding_repo.upsert(existing))
        return updated


class PerformanceCalculator:
    @staticmethod
    def summarize(portfolio: Portfolio, holdings: list[Holding]) -> dict[str, object]:
        invested = sum(h.market_value for h in holdings)
        total_value = portfolio.cash_balance + invested
        total_return = (
            (total_value - portfolio.initial_capital) / portfolio.initial_capital
            if portfolio.initial_capital > 0
            else Decimal("0")
        )
        return {
            "total_value": str(total_value),
            "cash_balance": str(portfolio.cash_balance),
            "invested_value": str(invested),
            "initial_capital": str(portfolio.initial_capital),
            "total_return": str(total_return.quantize(Decimal("0.000001"))),
            "holdings_count": len(holdings),
        }
