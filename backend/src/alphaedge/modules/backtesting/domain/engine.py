from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.dsl_executor import DSLStrategyExecutor
from alphaedge.modules.backtesting.domain.entities import BacktestTrade
from alphaedge.modules.backtesting.domain.enums import TradeSide
from alphaedge.modules.backtesting.domain.fill_simulator import FillSimulator
from alphaedge.modules.backtesting.domain.metrics import EquityPoint, MetricsCalculator
from alphaedge.modules.backtesting.domain.position_sizer import PositionSizer
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import StrategyCompiler
from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class BacktestOutput:
    result: object
    trades: list[BacktestTrade]


@dataclass
class _Portfolio:
    cash: Decimal
    positions: dict[UUID, Decimal] = field(default_factory=dict)
    open_trades: dict[UUID, BacktestTrade] = field(default_factory=dict)
    closed_trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)

    def position_qty(self, instrument_id: UUID) -> Decimal:
        return self.positions.get(instrument_id, Decimal("0"))

    def mark_equity(self, timestamp: datetime, prices: dict[UUID, Decimal]) -> None:
        holdings = sum(qty * prices.get(iid, Decimal("0")) for iid, qty in self.positions.items())
        self.equity_curve.append(EquityPoint(timestamp=timestamp, equity=self.cash + holdings))

    @property
    def equity(self) -> Decimal:
        return self.equity_curve[-1].equity if self.equity_curve else self.cash


class StrategyExecutor:
    """Protocol wrapper for DSL (and future Python) strategy execution."""

    def on_bar(self, bar: Bar) -> SignalAction | None:
        raise NotImplementedError


class DSLExecutorAdapter(StrategyExecutor):
    def __init__(self, executor: DSLStrategyExecutor) -> None:
        self._executor = executor

    def on_bar(self, bar: Bar) -> SignalAction | None:
        signal = self._executor.on_bar(bar)
        return signal.action if signal else None


class BacktestEngine:
    """Event-driven backtest engine processing bars in chronological order."""

    def __init__(self, run_id: UUID, config: BacktestConfig) -> None:
        self._run_id = run_id
        self._config = config

    def run(
        self,
        bars_by_instrument: dict[UUID, list[Bar]],
        strategy_type: StrategyType,
        source_code: str,
        strategy_name: str,
        parameters: dict[str, object],
    ) -> BacktestOutput:
        executor = self._build_executor(strategy_type, source_code, strategy_name, parameters)
        events = self._merge_events(bars_by_instrument)
        portfolio = _Portfolio(cash=self._config.initial_capital)
        latest_prices: dict[UUID, Decimal] = {}

        for bar in events:
            latest_prices[bar.instrument_id] = bar.close
            signal = executor.on_bar(bar)
            if signal:
                self._execute_signal(portfolio, bar, signal)
            portfolio.mark_equity(bar.timestamp, latest_prices)

        closed = portfolio.closed_trades
        if portfolio.open_trades:
            for iid, trade in list(portfolio.open_trades.items()):
                price = latest_prices.get(iid, trade.entry_price)
                ts = events[-1].timestamp if events else trade.entry_time
                self._close_position(portfolio, iid, price, ts)

        result = MetricsCalculator.compute(
            self._run_id,
            self._config.initial_capital,
            portfolio.equity_curve,
            closed,
        )
        for trade in closed:
            trade.backtest_run_id = self._run_id
        return BacktestOutput(result=result, trades=closed)

    def _build_executor(
        self,
        strategy_type: StrategyType,
        source_code: str,
        strategy_name: str,
        parameters: dict[str, object],
    ) -> StrategyExecutor:
        if strategy_type == StrategyType.DSL:
            compiled, _ = StrategyCompiler.validate_and_compile(
                StrategyType.DSL, source_code, strategy_name, parameters
            )
            return DSLExecutorAdapter(DSLStrategyExecutor(compiled))
        raise ValidationError(
            "Python strategy backtesting is not yet supported; use DSL strategies"
        )

    @staticmethod
    def _merge_events(bars_by_instrument: dict[UUID, list[Bar]]) -> list[Bar]:
        events: list[Bar] = []
        for bars in bars_by_instrument.values():
            events.extend(bars)
        events.sort(key=lambda b: b.timestamp)
        return events

    def _execute_signal(self, portfolio: _Portfolio, bar: Bar, signal: SignalAction) -> None:
        iid = bar.instrument_id
        price = bar.close
        equity = portfolio.equity if portfolio.equity_curve else portfolio.cash
        pos = portfolio.position_qty(iid)

        if signal == SignalAction.BUY and pos > 0:
            return
        if signal == SignalAction.SELL and pos <= 0:
            return

        if signal == SignalAction.SELL:
            self._close_position(portfolio, iid, price, bar.timestamp)
            return

        qty = PositionSizer.compute_quantity(
            signal, price, equity, portfolio.cash, pos, self._config
        )
        fill = FillSimulator.simulate(TradeSide.BUY, qty, price, self._config)
        if not fill:
            return
        cost = fill.fill_price * fill.quantity + fill.commission
        if cost > portfolio.cash:
            return
        portfolio.cash -= cost
        portfolio.positions[iid] = pos + fill.quantity
        trade = BacktestTrade.open(
            self._run_id,
            iid,
            fill.quantity,
            fill.fill_price,
            bar.timestamp,
            fill.commission,
            fill.slippage_amount,
        )
        portfolio.open_trades[iid] = trade

    def _close_position(
        self,
        portfolio: _Portfolio,
        instrument_id: UUID,
        price: Decimal,
        timestamp: datetime,
    ) -> None:
        pos = portfolio.position_qty(instrument_id)
        if pos <= 0:
            return
        fill = FillSimulator.simulate(TradeSide.SELL, pos, price, self._config)
        if not fill:
            return
        proceeds = fill.fill_price * fill.quantity - fill.commission
        portfolio.cash += proceeds
        portfolio.positions[instrument_id] = Decimal("0")
        trade = portfolio.open_trades.pop(instrument_id, None)
        if trade:
            trade.close(fill.fill_price, timestamp, fill.commission, fill.slippage_amount)
            portfolio.closed_trades.append(trade)
