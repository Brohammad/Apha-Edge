from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.dsl import INDICATOR_CALL, CompiledCondition
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


def _is_numeric_literal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except Exception:
        return False


@dataclass
class InstrumentIndicatorState:
    indicators: dict[str, Indicator] = field(default_factory=dict)
    prev_values: dict[str, Decimal | None] = field(default_factory=dict)
    current_values: dict[str, Decimal | None] = field(default_factory=dict)

    def get_indicator(self, ref: str, parameters: dict[str, object]) -> tuple[Indicator, str]:
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

    def resolve_operand(self, operand: str, parameters: dict[str, object]) -> Decimal | None:
        operand = operand.strip()
        if _is_numeric_literal(operand):
            return Decimal(operand)
        if operand in parameters:
            return Decimal(str(parameters[operand]))
        _, key = self.get_indicator(operand, parameters)
        return self.current_values.get(key)


class DSLStrategyExecutor:
    """Runtime executor for validated DSL strategies during backtesting."""

    def __init__(self, compiled) -> None:
        self._compiled = compiled
        self._states: dict[UUID, InstrumentIndicatorState] = {}

    def _collect_indicator_refs(self, cond: CompiledCondition, refs: set[str]) -> None:
        if cond.kind in ("crossover", "crossunder"):
            refs.add(cond.left)
            refs.add(cond.right)
        elif cond.kind == "compare":
            if INDICATOR_CALL.match(cond.operand_left.strip()):
                refs.add(cond.operand_left.strip())
            if INDICATOR_CALL.match(cond.operand_right.strip()):
                refs.add(cond.operand_right.strip())
        else:
            for child in cond.children:
                self._collect_indicator_refs(child, refs)

    def _evaluate(self, cond: CompiledCondition, state: InstrumentIndicatorState) -> bool:
        params = self._compiled.parameters
        if cond.kind == "crossover":
            _, left_key = state.get_indicator(cond.left, params)
            _, right_key = state.get_indicator(cond.right, params)
            left_val = state.current_values.get(left_key)
            right_val = state.current_values.get(right_key)
            if left_val is None or right_val is None:
                return False
            return crossover(
                state.prev_values.get(left_key),
                state.prev_values.get(right_key),
                left_val,
                right_val,
            )
        if cond.kind == "crossunder":
            _, left_key = state.get_indicator(cond.left, params)
            _, right_key = state.get_indicator(cond.right, params)
            left_val = state.current_values.get(left_key)
            right_val = state.current_values.get(right_key)
            if left_val is None or right_val is None:
                return False
            return crossunder(
                state.prev_values.get(left_key),
                state.prev_values.get(right_key),
                left_val,
                right_val,
            )
        if cond.kind == "compare":
            left_val = state.resolve_operand(cond.operand_left, params)
            right_val = state.resolve_operand(cond.operand_right, params)
            if left_val is None or right_val is None:
                return False
            if cond.operator == "lt":
                return left_val < right_val
            if cond.operator == "gt":
                return left_val > right_val
            if cond.operator == "lte":
                return left_val <= right_val
            if cond.operator == "gte":
                return left_val >= right_val
            if cond.operator == "eq":
                return left_val == right_val
            return False
        if cond.kind == "all":
            return all(self._evaluate(child, state) for child in cond.children)
        if cond.kind == "any":
            return any(self._evaluate(child, state) for child in cond.children)
        return False

    def on_bar(self, bar: Bar) -> Signal | None:
        state = self._states.setdefault(bar.instrument_id, InstrumentIndicatorState())
        close = bar.close

        refs: set[str] = set()
        for rule in self._compiled.signals:
            self._collect_indicator_refs(rule.condition_root, refs)
        for ref in refs:
            state.update_all(ref, self._compiled.parameters, close)

        for rule in self._compiled.signals:
            if self._evaluate(rule.condition_root, state):
                return Signal(
                    action=rule.action,
                    reason=rule.condition,
                    strength=rule.strength,
                    stop_loss_pct=rule.stop_loss_pct,
                    take_profit_pct=rule.take_profit_pct,
                )

        return None
