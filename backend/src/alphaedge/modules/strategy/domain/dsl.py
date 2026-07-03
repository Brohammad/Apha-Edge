import ast
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
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
CONDITION_FN = re.compile(r"^(?P<fn>crossover|crossunder|all|any)\s*\(", re.IGNORECASE)
COMPARE_OP = re.compile(r"^(?P<left>.+?)\s*(?P<op><=|>=|==|<|>)\s*(?P<right>.+)$")

_OP_MAP = {
    "<": "lt",
    ">": "gt",
    "<=": "lte",
    ">=": "gte",
    "==": "eq",
}


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


def _split_top_level_commas(inner: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(inner[start:i].strip())
            start = i + 1
    tail = inner[start:].strip()
    if tail:
        parts.append(tail)
    return parts


@dataclass(frozen=True)
class CompiledCondition:
    kind: str
    left: str = ""
    right: str = ""
    operator: str = ""
    operand_left: str = ""
    operand_right: str = ""
    children: tuple["CompiledCondition", ...] = ()


@dataclass(frozen=True)
class CompiledSignalRule:
    condition: str
    action: SignalAction
    condition_root: CompiledCondition
    # Legacy fields kept for C++ bridge compatibility
    left: str = ""
    right: str = ""
    condition_fn: str = ""
    strength: float | None = None
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None


@dataclass(frozen=True)
class CompiledStrategy:
    name: str
    parameters: dict[str, object]
    signals: tuple[CompiledSignalRule, ...]
    strategy_type: StrategyType

    def uses_advanced_dsl(self) -> bool:
        for rule in self.signals:
            if rule.condition_root.kind not in ("crossover", "crossunder"):
                return True
            if rule.strength is not None or rule.stop_loss_pct is not None:
                return True
        return False

    def to_canonical_json(self) -> str:
        payload = {
            "name": self.name,
            "parameters": self.parameters,
            "signals": [
                {
                    "condition": s.condition,
                    "action": s.action.value,
                    "condition_root": _condition_to_dict(s.condition_root),
                    "strength": s.strength,
                    "stop_loss_pct": s.stop_loss_pct,
                    "take_profit_pct": s.take_profit_pct,
                }
                for s in self.signals
            ],
            "strategy_type": self.strategy_type.value,
        }
        return json.dumps(payload, sort_keys=True)


def _condition_to_dict(cond: CompiledCondition) -> dict[str, object]:
    return {
        "kind": cond.kind,
        "left": cond.left,
        "right": cond.right,
        "operator": cond.operator,
        "operand_left": cond.operand_left,
        "operand_right": cond.operand_right,
        "children": [_condition_to_dict(c) for c in cond.children],
    }


def _parse_condition(expr: str) -> CompiledCondition:
    expr = expr.strip()
    match = CONDITION_FN.match(expr)
    if match:
        fn = match.group("fn").lower()
        rest = expr.strip()[match.end() :]
        if not rest.endswith(")"):
            raise ValidationError(f"Unsupported condition expression: {expr}")
        inner = rest[:-1]
        if fn in ("crossover", "crossunder"):
            left, right = _split_top_level_args(inner)
            return CompiledCondition(kind=fn, left=left, right=right)
        children = tuple(_parse_condition(part) for part in _split_top_level_commas(inner))
        if not children:
            raise ValidationError(f"{fn}() requires at least one sub-condition")
        return CompiledCondition(kind=fn, children=children)

    match = COMPARE_OP.match(expr)
    if match:
        left = match.group("left").strip()
        right = match.group("right").strip()
        op = _OP_MAP[match.group("op")]
        return CompiledCondition(
            kind="compare",
            operator=op,
            operand_left=left,
            operand_right=right,
        )

    match = re.match(r"^(?P<fn>crossover|crossunder)\s*\(", expr, re.IGNORECASE)
    if match:
        fn = match.group("fn").lower()
        rest = expr.strip()[match.end() :]
        if not rest.endswith(")"):
            raise ValidationError(f"Unsupported condition expression: {expr}")
        left, right = _split_top_level_args(rest[:-1])
        return CompiledCondition(kind=fn, left=left, right=right)

    raise ValidationError(f"Unsupported condition expression: {expr}")


def _validate_operand(ref: str, parameters: dict[str, object]) -> None:
    ref = ref.strip()
    if _is_numeric_literal(ref):
        return
    if ref in parameters:
        return
    DSLParser._validate_indicator_ref(ref, parameters)


def _is_numeric_literal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except Exception:
        return False


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
            for meta_key in ("strength", "stop_loss_pct", "take_profit_pct"):
                if meta_key in rule and rule[meta_key] is not None:
                    try:
                        float(rule[meta_key])
                    except (TypeError, ValueError) as exc:
                        raise ValidationError(
                            f"Signal rule {idx + 1} '{meta_key}' must be numeric"
                        ) from exc

    @staticmethod
    def _validate_condition(expr: str, parameters: dict[str, object]) -> None:
        cond = _parse_condition(expr)
        DSLParser._validate_condition_node(cond, parameters)

    @staticmethod
    def _validate_condition_node(cond: CompiledCondition, parameters: dict[str, object]) -> None:
        if cond.kind in ("crossover", "crossunder"):
            DSLParser._validate_indicator_ref(cond.left, parameters)
            DSLParser._validate_indicator_ref(cond.right, parameters)
        elif cond.kind == "compare":
            _validate_operand(cond.operand_left, parameters)
            _validate_operand(cond.operand_right, parameters)
        elif cond.kind in ("all", "any"):
            for child in cond.children:
                DSLParser._validate_condition_node(child, parameters)

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
            root = _parse_condition(when)
            signals.append(
                CompiledSignalRule(
                    condition=when,
                    action=SignalAction(str(rule["then"]).upper()),
                    condition_root=root,
                    left=root.left,
                    right=root.right,
                    condition_fn=root.kind if root.kind in ("crossover", "crossunder") else "",
                    strength=float(rule["strength"]) if rule.get("strength") is not None else None,
                    stop_loss_pct=(
                        float(rule["stop_loss_pct"])
                        if rule.get("stop_loss_pct") is not None
                        else None
                    ),
                    take_profit_pct=(
                        float(rule["take_profit_pct"])
                        if rule.get("take_profit_pct") is not None
                        else None
                    ),
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

        blocked_import_roots = frozenset(
            {"os", "sys", "subprocess", "socket", "pathlib", "shutil", "importlib", "builtins"}
        )
        blocked_calls = frozenset(
            {"eval", "exec", "compile", "open", "__import__", "getattr", "globals", "locals", "input"}
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in blocked_import_roots:
                        raise ValidationError(f"Disallowed import: {alias.name}")
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in blocked_import_roots:
                    raise ValidationError(f"Disallowed import: {node.module}")
            if isinstance(node, ast.Call):
                func = node.func
                name: str | None = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in blocked_calls:
                    raise ValidationError(f"Disallowed call: {name}")

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
