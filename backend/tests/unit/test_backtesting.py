from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.engine import BacktestEngine
from alphaedge.modules.backtesting.domain.enums import (
    PositionSizingModel,
    SlippageModel,
    TradeSide,
)
from alphaedge.modules.backtesting.domain.fill_simulator import FillSimulator
from alphaedge.modules.backtesting.domain.metrics import EquityPoint, MetricsCalculator
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.strategy.domain.enums import StrategyType
from alphaedge.shared.domain.exceptions import ValidationError

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


def _make_config(**overrides) -> BacktestConfig:
    defaults = {
        "instrument_ids": [str(uuid4())],
        "timeframe": "1d",
        "start_date": "2026-01-01T00:00:00+00:00",
        "end_date": "2026-06-01T00:00:00+00:00",
        "initial_capital": "100000",
        "slippage": {"model": "fixed", "value": "0.01"},
        "commission": {"per_trade": "1.0"},
        "position_sizing": {"model": "fixed_quantity", "value": "10"},
        "partial_fill_ratio": "1.0",
    }
    defaults.update(overrides)
    return BacktestConfig.from_dict(defaults)


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


class TestFillSimulator:
    def test_fixed_slippage_buy(self):
        config = _make_config()
        fill = FillSimulator.simulate(TradeSide.BUY, Decimal("10"), Decimal("100"), config)
        assert fill is not None
        assert fill.fill_price == Decimal("100.01")
        assert fill.commission == Decimal("1.0")

    def test_percentage_slippage_sell(self):
        config = _make_config(slippage={"model": "percentage", "value": "0.001"})
        fill = FillSimulator.simulate(TradeSide.SELL, Decimal("5"), Decimal("200"), config)
        assert fill is not None
        assert fill.fill_price == Decimal("200") - Decimal("200") * Decimal("0.001")

    def test_partial_fill(self):
        config = _make_config(partial_fill_ratio="0.5")
        fill = FillSimulator.simulate(TradeSide.BUY, Decimal("10"), Decimal("50"), config)
        assert fill is not None
        assert fill.quantity == Decimal("5.0000")


class TestMetricsCalculator:
    def test_total_return_and_drawdown(self):
        run_id = uuid4()
        curve = [
            EquityPoint(datetime(2026, 1, 1, tzinfo=UTC), Decimal("100000")),
            EquityPoint(datetime(2026, 1, 2, tzinfo=UTC), Decimal("110000")),
            EquityPoint(datetime(2026, 1, 3, tzinfo=UTC), Decimal("105000")),
        ]
        result = MetricsCalculator.compute(run_id, Decimal("100000"), curve, [])
        assert result.total_return == Decimal("0.05")
        assert result.max_drawdown > Decimal("0")


class TestBacktestEngine:
    def test_dsl_strategy_runs(self):
        iid = uuid4()
        config = _make_config(instrument_ids=[str(iid)])
        prices = [
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
        ]
        bars = _make_bars(iid, prices)
        engine = BacktestEngine(uuid4(), config)
        output = engine.run(
            bars_by_instrument={iid: bars},
            strategy_type=StrategyType.DSL,
            source_code=VALID_DSL,
            strategy_name="sma_crossover",
            parameters={"fast_period": 3, "slow_period": 5},
        )
        assert output.result.total_trades >= 0
        assert len(output.result.equity_curve) == len(bars)

    def test_python_strategy_rejected(self):
        config = _make_config()
        engine = BacktestEngine(uuid4(), config)
        with pytest.raises(ValidationError, match="Python strategy"):
            engine.run(
                bars_by_instrument={},
                strategy_type=StrategyType.PYTHON,
                source_code="class S(StrategyBase): pass",
                strategy_name="test",
                parameters={},
            )


class TestBacktestConfig:
    def test_from_dict(self):
        config = _make_config()
        assert config.slippage.model == SlippageModel.FIXED
        assert config.position_sizing.model == PositionSizingModel.FIXED_QUANTITY

    def test_invalid_dates(self):
        with pytest.raises(ValidationError):
            BacktestConfig.from_dict(
                {
                    "instrument_ids": [str(uuid4())],
                    "start_date": "2026-06-01T00:00:00+00:00",
                    "end_date": "2026-01-01T00:00:00+00:00",
                }
            )
