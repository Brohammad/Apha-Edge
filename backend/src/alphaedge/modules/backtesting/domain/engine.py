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
from alphaedge.modules.backtesting.domain.python_executor import PythonStrategyExecutor
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import StrategyCompiler
from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType
from alphaedge.modules.strategy.domain.value_objects import Signal


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
    signal_meta: dict[UUID, Signal] = field(default_factory=dict)

    def position_qty(self, instrument_id: UUID) -> Decimal:
        return self.positions.get(instrument_id, Decimal("0"))

    def mark_equity(self, timestamp: datetime, prices: dict[UUID, Decimal]) -> None:
        holdings = sum(qty * prices.get(iid, Decimal("0")) for iid, qty in self.positions.items())
        self.equity_curve.append(EquityPoint(timestamp=timestamp, equity=self.cash + holdings))

    @property
    def equity(self) -> Decimal:
        return self.equity_curve[-1].equity if self.equity_curve else self.cash


class StrategyExecutor:
    """Protocol wrapper for DSL and Python strategy execution."""

    def on_bar(self, bar: Bar) -> Signal | None:
        raise NotImplementedError

    def on_stop(self) -> None:
        pass


class DSLExecutorAdapter(StrategyExecutor):
    def __init__(self, executor: DSLStrategyExecutor) -> None:
        self._executor = executor

    def on_bar(self, bar: Bar) -> Signal | None:
        return self._executor.on_bar(bar)


class PythonExecutorAdapter(StrategyExecutor):
    def __init__(self, executor: PythonStrategyExecutor) -> None:
        self._executor = executor

    def on_bar(self, bar: Bar) -> Signal | None:
        return self._executor.on_bar(bar)

    def on_stop(self) -> None:
        self._executor.on_stop()


class BacktestEngine:
    """Event-driven backtest engine processing bars in chronological order.

    DSL strategies run on the C++ extension (``alphaedge_cpp``) when it is
    installed and ``settings.cpp_engine`` allows it; otherwise the pure-Python
    path below is used.
    """

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
        if (
            strategy_type == StrategyType.DSL
            and not self._config.allow_short
            and self._should_use_cpp(source_code, strategy_name, parameters)
        ):
            from alphaedge.modules.backtesting.domain.cpp_bridge import run_cpp_backtest

            compiled, _ = StrategyCompiler.validate_and_compile(
                StrategyType.DSL, source_code, strategy_name, parameters
            )
            return run_cpp_backtest(self._run_id, self._config, bars_by_instrument, compiled)

        executor = self._build_executor(strategy_type, source_code, strategy_name, parameters)
        events = self._merge_events(bars_by_instrument)
        portfolio = _Portfolio(cash=self._config.initial_capital)
        latest_prices: dict[UUID, Decimal] = {}

        for bar in events:
            latest_prices[bar.instrument_id] = bar.close
            self._check_risk_exits(portfolio, bar)
            signal = executor.on_bar(bar)
            if signal:
                self._execute_signal(portfolio, bar, signal)
            portfolio.mark_equity(bar.timestamp, latest_prices)

        executor.on_stop()

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
            allow_short=self._config.allow_short,
        )
        for trade in closed:
            trade.backtest_run_id = self._run_id
        return BacktestOutput(result=result, trades=closed)

    @staticmethod
    def _should_use_cpp(
        source_code: str,
        strategy_name: str,
        parameters: dict[str, object],
    ) -> bool:
        from alphaedge.config import settings
        from alphaedge.modules.backtesting.domain.cpp_bridge import cpp_available

        compiled, _ = StrategyCompiler.validate_and_compile(
            StrategyType.DSL, source_code, strategy_name, parameters
        )
        if compiled.uses_advanced_dsl():
            return False

        mode = settings.cpp_engine
        if mode == "off":
            return False
        if mode == "require":
            if not cpp_available():
                raise RuntimeError(
                    "cpp_engine is set to 'require' but alphaedge_cpp is not installed; "
                    "build it with `make build-cpp`"
                )
            return True
        return cpp_available()

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
        return PythonExecutorAdapter(PythonStrategyExecutor(source_code, parameters))

    @staticmethod
    def _merge_events(bars_by_instrument: dict[UUID, list[Bar]]) -> list[Bar]:
        events: list[Bar] = []
        for bars in bars_by_instrument.values():
            events.extend(bars)
        events.sort(key=lambda b: b.timestamp)
        return events

    def _check_risk_exits(self, portfolio: _Portfolio, bar: Bar) -> None:
        iid = bar.instrument_id
        meta = portfolio.signal_meta.get(iid)
        trade = portfolio.open_trades.get(iid)
        pos = portfolio.position_qty(iid)
        if not meta or not trade or pos == 0:
            return
        price = bar.close
        entry = trade.entry_price
        if entry <= 0:
            return
        if pos > 0:
            change_pct = float((price - entry) / entry * 100)
        else:
            change_pct = float((entry - price) / entry * 100)
        if meta.stop_loss_pct is not None and change_pct <= -meta.stop_loss_pct:
            self._close_position(portfolio, iid, price, bar.timestamp)
            portfolio.signal_meta.pop(iid, None)
            return
        if meta.take_profit_pct is not None and change_pct >= meta.take_profit_pct:
            self._close_position(portfolio, iid, price, bar.timestamp)
            portfolio.signal_meta.pop(iid, None)

    def _execute_signal(self, portfolio: _Portfolio, bar: Bar, signal: Signal) -> None:
        iid = bar.instrument_id
        pos = portfolio.position_qty(iid)
        action = signal.action

        if action == SignalAction.BUY:
            if pos > 0:
                return
            if pos < 0:
                self._close_position(portfolio, iid, bar.close, bar.timestamp)
                portfolio.signal_meta.pop(iid, None)
                return
            self._open_long(portfolio, bar, signal)
            return

        if action == SignalAction.SELL:
            if pos < 0:
                return
            if pos > 0:
                self._close_position(portfolio, iid, bar.close, bar.timestamp)
                portfolio.signal_meta.pop(iid, None)
                return
            if self._config.allow_short:
                self._open_short(portfolio, bar, signal)

    def _open_long(self, portfolio: _Portfolio, bar: Bar, signal: Signal) -> None:
        iid = bar.instrument_id
        price = bar.close
        equity = portfolio.equity if portfolio.equity_curve else portfolio.cash
        pos = portfolio.position_qty(iid)
        qty = PositionSizer.compute_quantity(
            SignalAction.BUY, price, equity, portfolio.cash, pos, self._config
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
            side="buy",
        )
        portfolio.open_trades[iid] = trade
        if signal.stop_loss_pct is not None or signal.take_profit_pct is not None:
            portfolio.signal_meta[iid] = signal

    def _open_short(self, portfolio: _Portfolio, bar: Bar, signal: Signal) -> None:
        iid = bar.instrument_id
        price = bar.close
        equity = portfolio.equity if portfolio.equity_curve else portfolio.cash
        qty = PositionSizer.compute_quantity(
            SignalAction.SELL, price, equity, portfolio.cash, Decimal("0"), self._config
        )
        fill = FillSimulator.simulate(TradeSide.SELL, qty, price, self._config)
        if not fill:
            return
        proceeds = fill.fill_price * fill.quantity - fill.commission
        portfolio.cash += proceeds
        portfolio.positions[iid] = -fill.quantity
        trade = BacktestTrade.open(
            self._run_id,
            iid,
            fill.quantity,
            fill.fill_price,
            bar.timestamp,
            fill.commission,
            fill.slippage_amount,
            side="sell",
        )
        portfolio.open_trades[iid] = trade
        if signal.stop_loss_pct is not None or signal.take_profit_pct is not None:
            portfolio.signal_meta[iid] = signal

    def _close_position(
        self,
        portfolio: _Portfolio,
        instrument_id: UUID,
        price: Decimal,
        timestamp: datetime,
    ) -> None:
        pos = portfolio.position_qty(instrument_id)
        if pos == 0:
            return
        trade = portfolio.open_trades.get(instrument_id)
        if pos > 0:
            fill = FillSimulator.simulate(TradeSide.SELL, pos, price, self._config)
            if not fill:
                return
            proceeds = fill.fill_price * fill.quantity - fill.commission
            portfolio.cash += proceeds
        else:
            qty = abs(pos)
            fill = FillSimulator.simulate(TradeSide.BUY, qty, price, self._config)
            if not fill:
                return
            cost = fill.fill_price * fill.quantity + fill.commission
            portfolio.cash -= cost
        portfolio.positions[instrument_id] = Decimal("0")
        open_trade = portfolio.open_trades.pop(instrument_id, trade)
        if open_trade:
            open_trade.close(fill.fill_price, timestamp, fill.commission, fill.slippage_amount)
            portfolio.closed_trades.append(open_trade)
