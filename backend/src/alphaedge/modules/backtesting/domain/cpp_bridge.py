"""Bridge between the domain backtest engine and the optional C++ extension.

The ``alphaedge_cpp`` module (built from ``backend/cpp``) accelerates the DSL
backtest hot path. Everything here converts domain objects to the flat
arrays the extension consumes and converts its output back into domain
entities. When the extension is not installed the engine falls back to the
pure-Python path.
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from functools import cache
from uuid import UUID, uuid4

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.entities import BacktestResult, BacktestTrade
from alphaedge.modules.backtesting.domain.enums import PositionSizingModel, SlippageModel
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import INDICATOR_CALL, CompiledStrategy
from alphaedge.modules.strategy.domain.enums import SignalAction

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)

_INDICATOR_KINDS = {"sma": 0, "ema": 1, "rsi": 2, "macd": 3, "bollinger": 4}
_CONDITION_FNS = {"crossover": 0, "crossunder": 1}
_ACTIONS = {SignalAction.BUY: 0, SignalAction.SELL: 1, SignalAction.HOLD: 2}

IndicatorSpec = tuple[int, int, int, int, float]
RuleSpec = tuple[int, int, int, int]


@cache
def cpp_available() -> bool:
    try:
        import alphaedge_cpp  # noqa: F401
    except ImportError:
        return False
    return True


def _to_micros(dt: datetime) -> int:
    return (dt - _EPOCH) // _MICROSECOND


def _from_micros(micros: int) -> datetime:
    return _EPOCH + timedelta(microseconds=micros)


def _dec(value: float, places: str = "0.00000001") -> Decimal:
    if not math.isfinite(value):
        raise ValueError(f"Non-finite value from C++ engine: {value}")
    # High precision so quantize never overflows the context for very large
    # equities (the default context is 28 significant digits).
    with localcontext() as ctx:
        ctx.prec = 400
        return Decimal(repr(value)).quantize(Decimal(places))


def _opt_dec(value: float, places: str = "0.00000001") -> Decimal | None:
    return None if math.isnan(value) else _dec(value, places)


def _opt_round4(value: float) -> Decimal | None:
    """Match MetricsCalculator's Decimal(str(round(x, 4))) for sharpe/sortino."""
    return None if math.isnan(value) else Decimal(str(round(value, 4)))


def _resolve_spec(name: str, arg: str, parameters: dict[str, object]) -> IndicatorSpec:
    if arg.isdigit():
        period = int(arg)
    else:
        raw = parameters.get(arg)
        if raw is None:
            raise ValueError(f"Unknown parameter: {arg}")
        period = int(raw)  # type: ignore[call-overload]
    if name == "macd":
        return (
            _INDICATOR_KINDS[name],
            int(parameters.get("fast_period", period)),  # type: ignore[call-overload]
            int(parameters.get("slow_period", 26)),  # type: ignore[call-overload]
            int(parameters.get("signal_period", 9)),  # type: ignore[call-overload]
            0.0,
        )
    if name == "bollinger":
        return (
            _INDICATOR_KINDS[name],
            period,
            0,
            0,
            float(parameters.get("std_dev", 2.0)),  # type: ignore[arg-type]
        )
    return (_INDICATOR_KINDS[name], period, 0, 0, 0.0)


def compile_for_cpp(compiled: CompiledStrategy) -> tuple[list[IndicatorSpec], list[RuleSpec]]:
    """Deduplicate indicator refs and encode signal rules for the extension.

    Refs are keyed by ``{name}_{arg}`` exactly like the Python
    ``DSLStrategyExecutor`` so shared indicators share state.
    """
    key_to_index: dict[str, int] = {}
    specs: list[IndicatorSpec] = []
    rules: list[RuleSpec] = []
    for rule in compiled.signals:
        indices: list[int] = []
        for ref in (rule.left, rule.right):
            match = INDICATOR_CALL.match(ref.strip())
            if not match:
                raise ValueError(f"Invalid indicator ref: {ref}")
            name = match.group("name").lower()
            arg = match.group("args").strip()
            key = f"{name}_{arg}"
            if key not in key_to_index:
                key_to_index[key] = len(specs)
                specs.append(_resolve_spec(name, arg, compiled.parameters))
            indices.append(key_to_index[key])
        rules.append(
            (
                indices[0],
                indices[1],
                _CONDITION_FNS[rule.condition_fn],
                _ACTIONS[rule.action],
            )
        )
    return specs, rules


def run_cpp_backtest(
    run_id: UUID,
    config: BacktestConfig,
    bars_by_instrument: dict[UUID, list[Bar]],
    compiled: CompiledStrategy,
):
    """Execute the backtest via the C++ engine, returning a BacktestOutput."""
    import alphaedge_cpp

    from alphaedge.modules.backtesting.domain.engine import BacktestOutput

    specs, rules = compile_for_cpp(compiled)

    instrument_ids = list(bars_by_instrument.keys())
    index_of = {iid: i for i, iid in enumerate(instrument_ids)}
    instrument: list[int] = []
    timestamps: list[int] = []
    closes: list[float] = []
    for iid, bars in bars_by_instrument.items():
        idx = index_of[iid]
        for bar in bars:
            instrument.append(idx)
            timestamps.append(_to_micros(bar.timestamp))
            closes.append(float(bar.close))

    raw = alphaedge_cpp.run_backtest(
        specs=specs,
        rules=rules,
        instrument=instrument,
        timestamp=timestamps,
        close=closes,
        n_instruments=len(instrument_ids),
        initial_capital=float(config.initial_capital),
        slippage_model=0 if config.slippage.model == SlippageModel.FIXED else 1,
        slippage_value=float(config.slippage.value),
        commission_per_trade=float(config.commission.per_trade),
        sizing_model=(
            0 if config.position_sizing.model == PositionSizingModel.FIXED_QUANTITY else 1
        ),
        sizing_value=float(config.position_sizing.value),
        partial_fill_ratio=float(config.partial_fill_ratio),
    )

    trades = [_trade_to_entity(t, run_id, instrument_ids) for t in raw["trades"]]
    result = _result_to_entity(raw, run_id, config, total_trades=len(trades))
    return BacktestOutput(result=result, trades=trades)


def _trade_to_entity(
    raw: dict[str, object],
    run_id: UUID,
    instrument_ids: list[UUID],
) -> BacktestTrade:
    quantity = _dec(raw["quantity"], "0.0001")  # type: ignore[arg-type]
    entry_price = _dec(raw["entry_price"])  # type: ignore[arg-type]
    exit_price = _dec(raw["exit_price"])  # type: ignore[arg-type]
    commission = _dec(raw["commission"])  # type: ignore[arg-type]
    # Recompute pnl in Decimal from the stored values so the persisted row is
    # internally consistent, mirroring BacktestTrade.close().
    pnl = (exit_price - entry_price) * quantity - commission
    return BacktestTrade(
        id=uuid4(),
        backtest_run_id=run_id,
        instrument_id=instrument_ids[raw["instrument"]],  # type: ignore[index]
        side="buy",
        quantity=quantity,
        entry_price=entry_price,
        entry_time=_from_micros(raw["entry_ts"]),  # type: ignore[arg-type]
        exit_price=exit_price,
        exit_time=_from_micros(raw["exit_ts"]),  # type: ignore[arg-type]
        pnl=pnl,
        commission=commission,
        slippage=_dec(raw["slippage"]),  # type: ignore[arg-type]
    )


def _result_to_entity(
    raw: dict[str, object],
    run_id: UUID,
    config: BacktestConfig,
    *,
    total_trades: int,
) -> BacktestResult:
    equity_ts: list[int] = raw["equity_ts"]  # type: ignore[assignment]
    equity: list[float] = raw["equity"]  # type: ignore[assignment]
    metrics: dict[str, float] = raw["metrics"]  # type: ignore[assignment]

    if not equity:
        return BacktestResult.create(
            backtest_run_id=run_id,
            total_return=Decimal("0"),
            max_drawdown=Decimal("0"),
            total_trades=total_trades,
            equity_curve=[],
            metrics={},
        )

    curve_json = [
        {"timestamp": _from_micros(ts).isoformat(), "equity": str(_dec(value))}
        for ts, value in zip(equity_ts, equity, strict=True)
    ]
    metrics_blob = {
        "initial_capital": str(config.initial_capital),
        "final_equity": str(_dec(metrics["final_equity"])),
        "days": int(metrics["days"]),
        "engine": "cpp",
    }
    return BacktestResult.create(
        backtest_run_id=run_id,
        total_return=_dec(metrics["total_return"]),
        max_drawdown=_dec(metrics["max_drawdown"]),
        total_trades=total_trades,
        equity_curve=curve_json,
        metrics=metrics_blob,
        annualized_return=_opt_dec(metrics["annualized_return"]),
        sharpe_ratio=_opt_round4(metrics["sharpe"]),
        sortino_ratio=_opt_round4(metrics["sortino"]),
        win_rate=_opt_dec(metrics["win_rate"]),
        profit_factor=_opt_dec(metrics["profit_factor"]),
    )
