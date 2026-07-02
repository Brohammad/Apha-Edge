"""Benchmark the Python vs C++ backtest engines.

Usage:
    python scripts/benchmark_backtest.py [--events N] [--py-events M]

Generates synthetic daily bars for one instrument and runs the same DSL
strategy through both engine paths. The Python engine is run on a smaller
sample by default (it is orders of magnitude slower) and its 1M-event time
is extrapolated from per-event throughput.

Phase 4b target: 1M events in < 5 seconds on the C++ path.
"""

import argparse
import math
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from alphaedge.config import settings
from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.cpp_bridge import cpp_available
from alphaedge.modules.backtesting.domain.engine import BacktestEngine
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.strategy.domain.enums import StrategyType

DSL = """
name: sma_crossover
parameters:
  fast_period: 10
  slow_period: 30
signals:
  - when: crossover(sma(fast_period), sma(slow_period))
    then: BUY
  - when: crossunder(sma(fast_period), sma(slow_period))
    then: SELL
"""
PARAMETERS = {"fast_period": 10, "slow_period": 30}


def generate_bars(instrument_id, count: int) -> list[Bar]:
    """Deterministic oscillating price series that produces regular crossovers."""
    bars: list[Bar] = []
    start = datetime(2000, 1, 1, tzinfo=UTC)
    step = timedelta(minutes=1)
    for i in range(count):
        price = Decimal(str(round(100.0 + 20.0 * math.sin(i / 40.0) + (i % 7) * 0.3, 4)))
        bars.append(
            Bar(
                instrument_id=instrument_id,
                timeframe=Timeframe.D1,
                timestamp=start + step * i,
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=Decimal("1000"),
            )
        )
    return bars


def make_config(instrument_id) -> BacktestConfig:
    return BacktestConfig.from_dict(
        {
            "instrument_ids": [str(instrument_id)],
            "timeframe": "1d",
            "start_date": "2000-01-01T00:00:00+00:00",
            "end_date": "2030-01-01T00:00:00+00:00",
            "initial_capital": "100000",
            "slippage": {"model": "fixed", "value": "0.01"},
            "commission": {"per_trade": "1.0"},
            # Fixed quantity keeps equity growth linear; percent-equity
            # compounding overflows a double over 1M synthetic bars.
            "position_sizing": {"model": "fixed_quantity", "value": "100"},
        }
    )


def run_engine(bars_by_instrument, config, mode: str) -> tuple[float, int]:
    settings.cpp_engine = mode
    engine = BacktestEngine(uuid4(), config)
    start = time.perf_counter()
    output = engine.run(
        bars_by_instrument=bars_by_instrument,
        strategy_type=StrategyType.DSL,
        source_code=DSL,
        strategy_name="sma_crossover",
        parameters=PARAMETERS,
    )
    elapsed = time.perf_counter() - start
    return elapsed, output.result.total_trades


def run_cpp_core(bars_by_instrument, config) -> float:
    """Time only the C++ extension call (excludes domain-object conversion)."""
    import alphaedge_cpp

    from alphaedge.modules.backtesting.domain.cpp_bridge import compile_for_cpp
    from alphaedge.modules.strategy.domain.dsl import StrategyCompiler

    compiled = StrategyCompiler.compile_dsl(DSL)
    specs, rules = compile_for_cpp(compiled)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    instrument, timestamps, closes = [], [], []
    for bars in bars_by_instrument.values():
        for bar in bars:
            instrument.append(0)
            timestamps.append(int((bar.timestamp - epoch).total_seconds() * 1_000_000))
            closes.append(float(bar.close))

    start = time.perf_counter()
    alphaedge_cpp.run_backtest(
        specs=specs,
        rules=rules,
        instrument=instrument,
        timestamp=timestamps,
        close=closes,
        n_instruments=1,
        initial_capital=100000.0,
        slippage_model=0,
        slippage_value=0.01,
        commission_per_trade=1.0,
        sizing_model=1,
        sizing_value=0.1,
        partial_fill_ratio=1.0,
    )
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=1_000_000, help="events for C++ path")
    parser.add_argument("--py-events", type=int, default=20_000, help="events for Python path")
    args = parser.parse_args()

    if not cpp_available():
        raise SystemExit("alphaedge_cpp is not installed; run `make build-cpp` first")

    iid = uuid4()
    config = make_config(iid)

    print(f"Generating {args.events:,} bars ...")
    bars = generate_bars(iid, args.events)
    bars_by_instrument = {iid: bars}

    print("Running C++ engine (end-to-end, incl. Decimal conversion) ...")
    cpp_time, cpp_trades = run_engine(bars_by_instrument, config, "require")
    print("Running C++ core (extension call only) ...")
    core_time = run_cpp_core(bars_by_instrument, config)

    py_bars = bars[: args.py_events]
    print(f"Running Python engine on {len(py_bars):,} bars ...")
    py_time, py_trades = run_engine({iid: py_bars}, config, "off")
    py_per_event = py_time / len(py_bars)
    py_extrapolated = py_per_event * args.events

    print()
    print(f"{'path':<28}{'events':>12}{'time':>12}{'events/sec':>16}")
    print("-" * 68)
    print(f"{'C++ core':<28}{args.events:>12,}{core_time:>11.3f}s{args.events / core_time:>16,.0f}")
    print(
        f"{'C++ end-to-end':<28}{args.events:>12,}{cpp_time:>11.3f}s"
        f"{args.events / cpp_time:>16,.0f}"
    )
    print(f"{'Python':<28}{len(py_bars):>12,}{py_time:>11.3f}s{len(py_bars) / py_time:>16,.0f}")
    print()
    print(f"C++ trades: {cpp_trades:,} | Python trades ({len(py_bars):,} bars): {py_trades:,}")
    print(f"Python extrapolated to {args.events:,} events: {py_extrapolated:,.1f}s")
    print(f"Speedup (core vs Python, per event): {py_per_event / (core_time / args.events):,.0f}x")
    target = "PASS" if core_time < 5.0 else "FAIL"
    print(f"Phase 4b target (1M events < 5s, C++ core): {target}")


if __name__ == "__main__":
    main()
