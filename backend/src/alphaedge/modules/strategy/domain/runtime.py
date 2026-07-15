"""Shared strategy runtime for backtests and live deployments."""

from __future__ import annotations

from alphaedge.modules.backtesting.domain.dsl_executor import DSLStrategyExecutor
from alphaedge.modules.backtesting.domain.strategy_runner import (
    StrategyRunner,
    create_strategy_runner,
)
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import StrategyCompiler
from alphaedge.modules.strategy.domain.enums import StrategyType
from alphaedge.modules.strategy.domain.value_objects import Signal


class StrategyRuntime:
    """Stateful strategy executor for a single strategy version."""

    def __init__(
        self,
        strategy_type: StrategyType,
        source_code: str,
        strategy_name: str,
        parameters: dict[str, object],
    ) -> None:
        if strategy_type == StrategyType.DSL:
            compiled, _ = StrategyCompiler.validate_and_compile(
                StrategyType.DSL, source_code, strategy_name, parameters
            )
            self._executor: DSLStrategyExecutor | StrategyRunner = DSLStrategyExecutor(compiled)
        else:
            self._executor = create_strategy_runner(source_code, parameters)

    def on_bar(self, bar: Bar) -> Signal | None:
        return self._executor.on_bar(bar)

    def on_stop(self) -> None:
        stop = getattr(self._executor, "on_stop", None)
        if callable(stop):
            stop()


_RUNTIME_CACHE: dict[str, StrategyRuntime] = {}


def get_runtime(
    cache_key: str,
    strategy_type: StrategyType,
    source_code: str,
    strategy_name: str,
    parameters: dict[str, object],
) -> StrategyRuntime:
    runtime = _RUNTIME_CACHE.get(cache_key)
    if runtime is None:
        runtime = StrategyRuntime(strategy_type, source_code, strategy_name, parameters)
        _RUNTIME_CACHE[cache_key] = runtime
    return runtime


def clear_runtime(cache_key: str) -> None:
    _RUNTIME_CACHE.pop(cache_key, None)
