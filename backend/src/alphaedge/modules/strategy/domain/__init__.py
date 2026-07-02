"""Strategy engine domain layer."""

from alphaedge.modules.strategy.domain.dsl import CompiledStrategy, DSLParser, StrategyCompiler
from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType, VersionStatus
from alphaedge.modules.strategy.domain.indicators import (
    EMA,
    INDICATOR_REGISTRY,
    MACD,
    RSI,
    SMA,
    BollingerBands,
    Indicator,
    StrategyBase,
    create_indicator,
    crossover,
    crossunder,
)
from alphaedge.modules.strategy.domain.repositories import (
    IndicatorRepository,
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.modules.strategy.domain.value_objects import (
    IndicatorDefinition,
    Signal,
    Strategy,
    StrategyContext,
    StrategyVersion,
    Tick,
)

__all__ = [
    "BollingerBands",
    "CompiledStrategy",
    "DSLParser",
    "EMA",
    "INDICATOR_REGISTRY",
    "Indicator",
    "IndicatorDefinition",
    "IndicatorRepository",
    "MACD",
    "RSI",
    "SMA",
    "Signal",
    "SignalAction",
    "Strategy",
    "StrategyBase",
    "StrategyCompiler",
    "StrategyContext",
    "StrategyRepository",
    "StrategyType",
    "StrategyVersion",
    "StrategyVersionRepository",
    "Tick",
    "VersionStatus",
    "create_indicator",
    "crossover",
    "crossunder",
]
