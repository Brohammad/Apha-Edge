from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import INDICATOR_CALL
from alphaedge.modules.strategy.domain.indicators import (
    Indicator,
    create_indicator,
    crossover,
    crossunder,
)
from alphaedge.modules.strategy.domain.value_objects import Signal


def _resolve_param(arg: str, parameters: dict[str, object]) -> dict[str, object]:
    if arg.isdigit():
        return {"period": int(arg)}
    value = parameters.get(arg)
    if value is None:
        raise ValueError(f"Unknown parameter: {arg}")
    return {"period": int(value)}


def _indicator_key(name: str, arg: str) -> str:
    return f"{name.lower()}_{arg}"


@dataclass
class InstrumentIndicatorState:
    indicators: dict[str, Indicator] = field(default_factory=dict)
    prev_values: dict[str, Decimal | None] = field(default_factory=dict)
    current_values: dict[str, Decimal | None] = field(default_factory=dict)

    def get_indicator(
        self, ref: str, parameters: dict[str, object]
    ) -> tuple[Indicator, str]:
        match = INDICATOR_CALL.match(ref.strip())
        if not match:
            raise ValueError(f"Invalid indicator ref: {ref}")
        name = match.group("name").lower()
        arg = match.group("args").strip()
        key = _indicator_key(name, arg)
        if key not in self.indicators:
            params = _resolve_param(arg, parameters)
            if name == "macd":
                params = {
                    "fast_period": int(parameters.get("fast_period", params.get("period", 12))),
                    "slow_period": int(parameters.get("slow_period", 26)),
                    "signal_period": int(parameters.get("signal_period", 9)),
                }
            elif name == "bollinger":
                params = {
                    "period": params.get("period", 20),
                    "std_dev": float(parameters.get("std_dev", 2.0)),
                }
            self.indicators[key] = create_indicator(name, params)
            self.prev_values[key] = None
            self.current_values[key] = None
        return self.indicators[key], key

    def update_all(self, ref: str, parameters: dict[str, object], close: Decimal) -> None:
        indicator, key = self.get_indicator(ref, parameters)
        self.prev_values[key] = self.current_values.get(key)
        self.current_values[key] = indicator.update(close)


class DSLStrategyExecutor:
    """Runtime executor for validated DSL strategies during backtesting."""

    def __init__(self, compiled) -> None:
        self._compiled = compiled
        self._states: dict[UUID, InstrumentIndicatorState] = {}

    def on_bar(self, bar: Bar) -> Signal | None:
        state = self._states.setdefault(bar.instrument_id, InstrumentIndicatorState())
        close = bar.close

        refs: set[str] = set()
        for rule in self._compiled.signals:
            refs.add(rule.left)
            refs.add(rule.right)
        for ref in refs:
            state.update_all(ref, self._compiled.parameters, close)

        for rule in self._compiled.signals:
            _, left_key = state.get_indicator(rule.left, self._compiled.parameters)
            _, right_key = state.get_indicator(rule.right, self._compiled.parameters)
            left_val = state.current_values.get(left_key)
            right_val = state.current_values.get(right_key)
            if left_val is None or right_val is None:
                continue

            prev_left = state.prev_values.get(left_key)
            prev_right = state.prev_values.get(right_key)

            triggered = False
            if rule.condition_fn == "crossover":
                triggered = crossover(prev_left, prev_right, left_val, right_val)
            elif rule.condition_fn == "crossunder":
                triggered = crossunder(prev_left, prev_right, left_val, right_val)

            if triggered:
                return Signal(action=rule.action, reason=rule.condition)

        return None
