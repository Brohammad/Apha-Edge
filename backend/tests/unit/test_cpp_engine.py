"""Tests for the optional C++ backtest engine (Phase 4b).

Parity tests are skipped when the ``alphaedge_cpp`` extension is not built.
Fallback tests always run.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.config import settings
from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.cpp_bridge import compile_for_cpp, cpp_available
from alphaedge.modules.backtesting.domain.engine import BacktestEngine
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.strategy.domain.dsl import StrategyCompiler
from alphaedge.modules.strategy.domain.enums import StrategyType

VALID_DSL = """
name: sma_crossover
parameters:
  fast_period: 3
  slow_period: 5
signals:
  - when: crossover(sma(fast_period), sma(slow_period))
    then: BUY
  - when: crossunder(sma(fast_period), sma(slow_period))
    then: SELL
"""
PARAMETERS = {"fast_period": 3, "slow_period": 5}

PRICES = [
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "14",
    "13",
    "12",
    "11",
    "10",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "14",
    "12",
    "10",
    "11",
    "13",
    "15",
]


def _make_bars(instrument_id, prices: list[str]) -> list[Bar]:
    bars = []
    for i, price in enumerate(prices):
        p = Decimal(price)
        bars.append(
            Bar(
                instrument_id=instrument_id,
                timeframe=Timeframe.D1,
                timestamp=datetime(2026, 1, 1 + i, tzinfo=UTC),
                open=p,
                high=p + Decimal("1"),
                low=p - Decimal("1"),
                close=p,
                volume=Decimal("1000"),
            )
        )
    return bars


def _make_config(instrument_ids: list, **overrides) -> BacktestConfig:
    defaults = {
        "instrument_ids": [str(i) for i in instrument_ids],
        "timeframe": "1d",
        "start_date": "2026-01-01T00:00:00+00:00",
        "end_date": "2026-06-01T00:00:00+00:00",
        "initial_capital": "100000",
        "slippage": {"model": "fixed", "value": "0.01"},
        "commission": {"per_trade": "1.0"},
        "position_sizing": {"model": "percent_equity", "value": "0.1"},
    }
    defaults.update(overrides)
    return BacktestConfig.from_dict(defaults)


def _run(bars_by_instrument, config, mode: str, monkeypatch):
    monkeypatch.setattr(settings, "cpp_engine", mode)
    engine = BacktestEngine(uuid4(), config)
    return engine.run(
        bars_by_instrument=bars_by_instrument,
        strategy_type=StrategyType.DSL,
        source_code=VALID_DSL,
        strategy_name="sma_crossover",
        parameters=PARAMETERS,
    )


class TestCompileForCpp:
    def test_shared_indicator_refs_deduplicated(self):
        compiled = StrategyCompiler.compile_dsl(VALID_DSL)
        specs, rules = compile_for_cpp(compiled)
        assert len(specs) == 2  # sma(fast), sma(slow) shared across both rules
        assert specs[0] == (0, 3, 0, 0, 0.0)
        assert specs[1] == (0, 5, 0, 0, 0.0)
        assert rules == [(0, 1, 0, 0), (0, 1, 1, 1)]


class TestFallback:
    def test_off_mode_uses_python_path(self, monkeypatch):
        iid = uuid4()
        config = _make_config([iid])
        output = _run({iid: _make_bars(iid, PRICES)}, config, "off", monkeypatch)
        # Python path does not stamp an engine marker into metrics.
        assert output.result.metrics.get("engine") != "cpp"

    def test_require_mode_raises_without_extension(self, monkeypatch):
        from alphaedge.modules.backtesting.domain import cpp_bridge

        monkeypatch.setattr(cpp_bridge, "cpp_available", lambda: False)
        monkeypatch.setattr(settings, "cpp_engine", "require")
        engine = BacktestEngine(uuid4(), _make_config([uuid4()]))
        with pytest.raises(RuntimeError, match="alphaedge_cpp is not installed"):
            engine.run(
                bars_by_instrument={},
                strategy_type=StrategyType.DSL,
                source_code=VALID_DSL,
                strategy_name="sma_crossover",
                parameters=PARAMETERS,
            )


@pytest.mark.skipif(not cpp_available(), reason="alphaedge_cpp extension not built")
class TestCppParity:
    def test_single_instrument_matches_python(self, monkeypatch):
        iid = uuid4()
        config = _make_config([iid])
        bars = {iid: _make_bars(iid, PRICES)}

        py = _run(bars, config, "off", monkeypatch)
        cpp = _run(bars, config, "require", monkeypatch)

        assert cpp.result.metrics.get("engine") == "cpp"
        assert cpp.result.total_trades == py.result.total_trades
        assert len(cpp.result.equity_curve) == len(py.result.equity_curve)
        for p_pt, c_pt in zip(py.result.equity_curve, cpp.result.equity_curve, strict=True):
            assert float(c_pt["equity"]) == pytest.approx(float(p_pt["equity"]), rel=1e-9)
        assert float(cpp.result.total_return) == pytest.approx(
            float(py.result.total_return), abs=1e-8
        )
        assert float(cpp.result.max_drawdown) == pytest.approx(
            float(py.result.max_drawdown), abs=1e-8
        )
        assert cpp.result.sharpe_ratio == py.result.sharpe_ratio

        for p_tr, c_tr in zip(py.trades, cpp.trades, strict=True):
            assert c_tr.instrument_id == p_tr.instrument_id
            assert c_tr.entry_time == p_tr.entry_time
            assert c_tr.exit_time == p_tr.exit_time
            assert float(c_tr.quantity) == pytest.approx(float(p_tr.quantity), abs=1e-4)
            assert float(c_tr.entry_price) == pytest.approx(float(p_tr.entry_price), abs=1e-8)
            assert float(c_tr.pnl) == pytest.approx(float(p_tr.pnl), rel=1e-9)

    def test_multi_instrument_matches_python(self, monkeypatch):
        iid_a, iid_b = uuid4(), uuid4()
        config = _make_config([iid_a, iid_b])
        prices_b = list(reversed(PRICES))
        bars = {iid_a: _make_bars(iid_a, PRICES), iid_b: _make_bars(iid_b, prices_b)}

        py = _run(bars, config, "off", monkeypatch)
        cpp = _run(bars, config, "require", monkeypatch)

        assert cpp.result.total_trades == py.result.total_trades
        assert len(cpp.result.equity_curve) == len(py.result.equity_curve)
        py_final = float(py.result.equity_curve[-1]["equity"])
        cpp_final = float(cpp.result.equity_curve[-1]["equity"])
        assert cpp_final == pytest.approx(py_final, rel=1e-9)

    def test_fixed_quantity_and_percentage_slippage(self, monkeypatch):
        iid = uuid4()
        config = _make_config(
            [iid],
            slippage={"model": "percentage", "value": "0.001"},
            position_sizing={"model": "fixed_quantity", "value": "10"},
        )
        bars = {iid: _make_bars(iid, PRICES)}

        py = _run(bars, config, "off", monkeypatch)
        cpp = _run(bars, config, "require", monkeypatch)

        assert cpp.result.total_trades == py.result.total_trades
        for p_tr, c_tr in zip(py.trades, cpp.trades, strict=True):
            assert float(c_tr.entry_price) == pytest.approx(float(p_tr.entry_price), rel=1e-12)
            assert float(c_tr.slippage) == pytest.approx(float(p_tr.slippage), rel=1e-12)

    def test_empty_bars(self, monkeypatch):
        iid = uuid4()
        config = _make_config([iid])
        cpp = _run({iid: []}, config, "require", monkeypatch)
        assert cpp.result.total_trades == 0
        assert cpp.result.equity_curve == []
        assert cpp.result.total_return == Decimal("0")
