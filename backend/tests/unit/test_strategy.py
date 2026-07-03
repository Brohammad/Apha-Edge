from decimal import Decimal

import pytest

from alphaedge.modules.strategy.domain.dsl import DSLParser, StrategyCompiler
from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType
from alphaedge.modules.strategy.domain.indicators import (
    EMA,
    MACD,
    RSI,
    SMA,
    BollingerBands,
    crossover,
    crossunder,
)
from alphaedge.shared.domain.exceptions import ValidationError

VALID_DSL = """
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

VALID_PYTHON = """
from alphaedge.modules.strategy.domain import StrategyBase, Signal, SignalAction

class MyStrategy(StrategyBase):
    def on_bar(self, bar, context):
        return Signal(action=SignalAction.HOLD)
"""


class TestDSLParser:
    def test_parse_valid_dsl(self):
        data = DSLParser.parse(VALID_DSL)
        DSLParser.validate(data)
        assert data["name"] == "sma_crossover"
        assert len(data["signals"]) == 2

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError, match="name"):
            DSLParser.validate(
                {"signals": [{"when": "crossover(sma(10), sma(20))", "then": "BUY"}]}
            )

    def test_invalid_indicator_raises(self):
        dsl = """
name: bad
signals:
  - when: crossover(foo(10), sma(20))
    then: BUY
"""
        data = DSLParser.parse(dsl)
        with pytest.raises(ValidationError, match="Invalid indicator"):
            DSLParser.validate(data)

    def test_unknown_parameter_raises(self):
        dsl = """
name: bad
parameters:
  fast_period: 10
signals:
  - when: crossover(sma(unknown_param), sma(slow_period))
    then: BUY
"""
        data = DSLParser.parse(dsl)
        with pytest.raises(ValidationError, match="Unknown parameter"):
            DSLParser.validate(data)


class TestStrategyCompiler:
    def test_compile_dsl(self):
        compiled, hash_val = StrategyCompiler.validate_and_compile(
            StrategyType.DSL, VALID_DSL, "sma_crossover"
        )
        assert compiled.name == "sma_crossover"
        assert compiled.strategy_type == StrategyType.DSL
        assert len(compiled.signals) == 2
        assert compiled.signals[0].action == SignalAction.BUY
        assert len(hash_val) == 64

    def test_compile_python(self):
        compiled, hash_val = StrategyCompiler.validate_and_compile(
            StrategyType.PYTHON, VALID_PYTHON, "my_strategy", {"period": 20}
        )
        assert compiled.strategy_type == StrategyType.PYTHON
        assert len(hash_val) == 64

    def test_python_syntax_error(self):
        with pytest.raises(ValidationError, match="syntax"):
            StrategyCompiler.validate_python("def broken(")

    def test_python_missing_base_class(self):
        with pytest.raises(ValidationError, match="StrategyBase"):
            StrategyCompiler.validate_and_compile(StrategyType.PYTHON, "class Foo: pass", "foo")

    def test_python_disallowed_import(self):
        with pytest.raises(ValidationError, match="Disallowed import"):
            StrategyCompiler.validate_python("import os\nclass S(StrategyBase): pass")


class TestSMA:
    def test_not_ready_until_period(self):
        sma = SMA(3)
        assert sma.update(Decimal("10")) is None
        assert sma.update(Decimal("20")) is None
        result = sma.update(Decimal("30"))
        assert result == Decimal("20")

    def test_reset(self):
        sma = SMA(2)
        sma.update(Decimal("10"))
        sma.reset()
        assert not sma.ready


class TestEMA:
    def test_produces_value_after_period(self):
        ema = EMA(3)
        ema.update(Decimal("10"))
        ema.update(Decimal("20"))
        result = ema.update(Decimal("30"))
        assert result is not None


class TestRSI:
    def test_rsi_range(self):
        rsi = RSI(2)
        rsi.update(Decimal("44"))
        rsi.update(Decimal("44.34"))
        rsi.update(Decimal("44.09"))
        value = rsi.update(Decimal("43.61"))
        assert value is not None
        assert Decimal("0") <= value <= Decimal("100")


class TestMACD:
    def test_macd_eventually_ready(self):
        macd = MACD(fast_period=2, slow_period=3, signal_period=2)
        values = [Decimal(str(v)) for v in range(1, 20)]
        outputs = [macd.update(v) for v in values]
        assert any(o is not None for o in outputs)


class TestBollingerBands:
    def test_bands(self):
        bb = BollingerBands(period=3, std_dev=2.0)
        for price in [Decimal("10"), Decimal("11"), Decimal("12")]:
            bb.update(price)
        assert bb.middle is not None
        assert bb.upper is not None
        assert bb.lower is not None
        assert bb.upper > bb.middle > bb.lower


class TestCrossover:
    def test_crossover_detected(self):
        assert crossover(Decimal("9"), Decimal("10"), Decimal("11"), Decimal("10"))

    def test_crossunder_detected(self):
        assert crossunder(Decimal("11"), Decimal("10"), Decimal("9"), Decimal("10"))

    def test_no_crossover_without_history(self):
        assert not crossover(None, None, Decimal("11"), Decimal("10"))


class TestDSLComparisons:
    def test_rsi_oversold_dsl_validates(self):
        dsl = """
name: rsi_mean_reversion
parameters:
  rsi_period: 14
  oversold: 30
  overbought: 70
signals:
  - when: rsi(rsi_period) < oversold
    then: BUY
  - when: rsi(rsi_period) > overbought
    then: SELL
"""
        data = DSLParser.parse(dsl)
        DSLParser.validate(data)
        compiled, _ = StrategyCompiler.validate_and_compile(
            StrategyType.DSL, dsl, "rsi_mean_reversion"
        )
        assert compiled.signals[0].condition_root.kind == "compare"

    def test_all_condition_validates(self):
        dsl = """
name: combo
parameters:
  fast: 10
  slow: 30
signals:
  - when: all(crossover(sma(fast), sma(slow)), rsi(14) < 30)
    then: BUY
"""
        data = DSLParser.parse(dsl)
        DSLParser.validate(data)
        compiled, _ = StrategyCompiler.validate_and_compile(StrategyType.DSL, dsl, "combo")
        assert compiled.signals[0].condition_root.kind == "all"
        assert len(compiled.signals[0].condition_root.children) == 2
