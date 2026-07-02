import ast
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

import yaml

from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType
from alphaedge.modules.strategy.domain.indicators import INDICATOR_REGISTRY
from alphaedge.shared.domain.exceptions import ValidationError

ALLOWED_INDICATORS = frozenset(INDICATOR_REGISTRY.keys())
ALLOWED_ACTIONS = frozenset(a.value for a in SignalAction)
INDICATOR_CALL = re.compile(
    r"^(?P<name>sma|ema|rsi|macd|bollinger)\((?P<args>[^)]*)\)$",
    re.IGNORECASE,
)
CONDITION_FN = re.compile(r"^(?P<fn>crossover|crossunder)\s*\(", re.IGNORECASE)


def _split_top_level_args(inner: str) -> tuple[str, str]:
    depth = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return inner[:i].strip(), inner[i + 1 :].strip()
    raise ValidationError(f"Invalid condition arguments: {inner}")


def _parse_condition(expr: str) -> tuple[str, str, str]:
    match = CONDITION_FN.match(expr.strip())
    if not match:
        raise ValidationError(f"Unsupported condition expression: {expr}")
    fn = match.group("fn").lower()
    rest = expr.strip()[match.end() :]
    if not rest.endswith(")"):
        raise ValidationError(f"Unsupported condition expression: {expr}")
    left, right = _split_top_level_args(rest[:-1])
    return fn, left, right


@dataclass(frozen=True)
class CompiledSignalRule:
    condition: str
    action: SignalAction
    left: str
    right: str
    condition_fn: str


@dataclass(frozen=True)
class CompiledStrategy:
    name: str
    parameters: dict[str, object]
    signals: tuple[CompiledSignalRule, ...]
    strategy_type: StrategyType

    def to_canonical_json(self) -> str:
        payload = {
            "name": self.name,
            "parameters": self.parameters,
            "signals": [
                {
                    "condition": s.condition,
                    "action": s.action.value,
                    "left": s.left,
                    "right": s.right,
                    "condition_fn": s.condition_fn,
                }
                for s in self.signals
            ],
            "strategy_type": self.strategy_type.value,
        }
        return json.dumps(payload, sort_keys=True)


class DSLParser:
    """Parse and validate YAML strategy definitions."""

    @staticmethod
    def parse(source: str) -> dict[str, Any]:
        try:
            data = yaml.safe_load(source)
        except yaml.YAMLError as exc:
            raise ValidationError(f"Invalid YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise ValidationError("Strategy DSL must be a YAML mapping")
        return data

    @staticmethod
    def validate(data: dict[str, Any]) -> None:
        name = data.get("name")
        if not name or not isinstance(name, str):
            raise ValidationError("DSL requires a non-empty 'name' string")

        parameters = data.get("parameters", {})
        if parameters is not None and not isinstance(parameters, dict):
            raise ValidationError("'parameters' must be a mapping")

        signals = data.get("signals")
        if not signals or not isinstance(signals, list):
            raise ValidationError("DSL requires at least one signal rule")

        for idx, rule in enumerate(signals):
            if not isinstance(rule, dict):
                raise ValidationError(f"Signal rule {idx + 1} must be a mapping")
            when = rule.get("when")
            then = rule.get("then")
            if not when or not isinstance(when, str):
                raise ValidationError(f"Signal rule {idx + 1} requires 'when' expression")
            if not then or str(then).upper() not in ALLOWED_ACTIONS:
                raise ValidationError(f"Signal rule {idx + 1} requires valid 'then' action")
            DSLParser._validate_condition(when.strip(), parameters or {})

    @staticmethod
    def _validate_condition(expr: str, parameters: dict[str, object]) -> None:
        _, left, right = _parse_condition(expr)
        DSLParser._validate_indicator_ref(left, parameters)
        DSLParser._validate_indicator_ref(right, parameters)

    @staticmethod
    def _validate_indicator_ref(ref: str, parameters: dict[str, object]) -> None:
        match = INDICATOR_CALL.match(ref)
        if not match:
            raise ValidationError(f"Invalid indicator reference: {ref}")
        name = match.group("name").lower()
        if name not in ALLOWED_INDICATORS:
            raise ValidationError(f"Unknown indicator: {name}")
        args = match.group("args").strip()
        if args:
            for arg in args.split(","):
                arg = arg.strip()
                if arg and arg not in parameters and not arg.isdigit():
                    raise ValidationError(f"Unknown parameter reference: {arg}")


class StrategyCompiler:
    """Compile and validate Python or DSL strategies."""

    @staticmethod
    def compile_dsl(source: str) -> CompiledStrategy:
        data = DSLParser.parse(source)
        DSLParser.validate(data)
        parameters = dict(data.get("parameters") or {})
        signals: list[CompiledSignalRule] = []
        for rule in data["signals"]:
            when = rule["when"].strip()
            fn, left, right = _parse_condition(when)
            signals.append(
                CompiledSignalRule(
                    condition=when,
                    action=SignalAction(str(rule["then"]).upper()),
                    left=left,
                    right=right,
                    condition_fn=fn,
                )
            )
        return CompiledStrategy(
            name=data["name"],
            parameters=parameters,
            signals=tuple(signals),
            strategy_type=StrategyType.DSL,
        )

    @staticmethod
    def validate_python(source: str) -> None:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ValidationError(f"Python syntax error: {exc}") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("os", "sys", "subprocess", "socket")):
                        raise ValidationError(f"Disallowed import: {alias.name}")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".")[0]
                in (
                    "os",
                    "sys",
                    "subprocess",
                    "socket",
                )
            ):
                raise ValidationError(f"Disallowed import: {node.module}")

    @staticmethod
    def compile_python(source: str, name: str, parameters: dict[str, object]) -> CompiledStrategy:
        StrategyCompiler.validate_python(source)
        if "StrategyBase" not in source:
            raise ValidationError("Python strategy must subclass StrategyBase")
        return CompiledStrategy(
            name=name,
            parameters=parameters,
            signals=(),
            strategy_type=StrategyType.PYTHON,
        )

    @staticmethod
    def compile_hash(compiled: CompiledStrategy) -> str:
        return hashlib.sha256(compiled.to_canonical_json().encode()).hexdigest()

    @classmethod
    def validate_and_compile(
        cls,
        strategy_type: StrategyType,
        source_code: str,
        name: str,
        parameters: dict[str, object] | None = None,
    ) -> tuple[CompiledStrategy, str]:
        params = parameters or {}
        if strategy_type == StrategyType.DSL:
            compiled = cls.compile_dsl(source_code)
        else:
            compiled = cls.compile_python(source_code, name, params)
        return compiled, cls.compile_hash(compiled)
