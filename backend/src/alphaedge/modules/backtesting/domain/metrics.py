import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from alphaedge.modules.backtesting.domain.entities import BacktestResult, BacktestTrade


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    equity: Decimal


class MetricsCalculator:
    @staticmethod
    def compute(
        backtest_run_id,
        initial_capital: Decimal,
        equity_curve: list[EquityPoint],
        trades: list[BacktestTrade],
    ) -> BacktestResult:
        if not equity_curve:
            return BacktestResult.create(
                backtest_run_id=backtest_run_id,
                total_return=Decimal("0"),
                max_drawdown=Decimal("0"),
                total_trades=len(trades),
                equity_curve=[],
                metrics={},
            )

        final_equity = equity_curve[-1].equity
        total_return = (final_equity - initial_capital) / initial_capital

        days = max(
            (equity_curve[-1].timestamp - equity_curve[0].timestamp).days,
            1,
        )
        years = Decimal(days) / Decimal("365")
        annualized = None
        if years > 0 and final_equity > 0 and initial_capital > 0:
            ratio = float(final_equity / initial_capital)
            annualized = Decimal(str(ratio ** (float(Decimal("1") / years) - 1)))

        returns = MetricsCalculator._daily_returns(equity_curve)
        sharpe = MetricsCalculator._sharpe(returns)
        sortino = MetricsCalculator._sortino(returns)
        max_dd = MetricsCalculator._max_drawdown(equity_curve)
        win_rate, profit_factor = MetricsCalculator._trade_stats(trades)

        curve_json = [
            {"timestamp": p.timestamp.isoformat(), "equity": str(p.equity)} for p in equity_curve
        ]
        metrics_blob = {
            "initial_capital": str(initial_capital),
            "final_equity": str(final_equity),
            "days": days,
        }

        return BacktestResult.create(
            backtest_run_id=backtest_run_id,
            total_return=total_return,
            max_drawdown=max_dd,
            total_trades=len(trades),
            equity_curve=curve_json,
            metrics=metrics_blob,
            annualized_return=annualized,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

    @staticmethod
    def _daily_returns(curve: list[EquityPoint]) -> list[float]:
        returns: list[float] = []
        for i in range(1, len(curve)):
            prev = curve[i - 1].equity
            curr = curve[i].equity
            if prev > 0:
                returns.append(float((curr - prev) / prev))
        return returns

    @staticmethod
    def _sharpe(returns: list[float], risk_free: float = 0.0) -> Decimal | None:
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return None
        sharpe = (mean - risk_free) / std * math.sqrt(252)
        return Decimal(str(round(sharpe, 4)))

    @staticmethod
    def _sortino(returns: list[float], risk_free: float = 0.0) -> Decimal | None:
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        downside = [min(0, r - risk_free) ** 2 for r in returns]
        downside_dev = math.sqrt(sum(downside) / len(downside))
        if downside_dev == 0:
            return None
        sortino = (mean - risk_free) / downside_dev * math.sqrt(252)
        return Decimal(str(round(sortino, 4)))

    @staticmethod
    def _max_drawdown(curve: list[EquityPoint]) -> Decimal:
        peak = curve[0].equity
        max_dd = Decimal("0")
        for point in curve:
            if point.equity > peak:
                peak = point.equity
            if peak > 0:
                dd = (peak - point.equity) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    @staticmethod
    def _trade_stats(
        trades: list[BacktestTrade],
    ) -> tuple[Decimal | None, Decimal | None]:
        closed = [t for t in trades if t.pnl is not None]
        if not closed:
            return None, None
        wins = [t for t in closed if t.pnl and t.pnl > 0]
        win_rate = Decimal(len(wins)) / Decimal(len(closed))
        gross_profit = sum(t.pnl for t in wins if t.pnl)
        losses = [t for t in closed if t.pnl and t.pnl < 0]
        gross_loss = abs(sum(t.pnl for t in losses if t.pnl))
        profit_factor = None
        if gross_loss > 0:
            profit_factor = Decimal(str(gross_profit / gross_loss))
        return win_rate, profit_factor
