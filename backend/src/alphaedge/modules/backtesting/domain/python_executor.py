"""Runtime executor for validated Python strategies during backtesting."""

from __future__ import annotations

import ast
import builtins
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.enums import SignalAction
from alphaedge.modules.strategy.domain.indicators import (
    EMA,
    MACD,
    RSI,
    SMA,
    BollingerBands,
    StrategyBase,
    create_indicator,
    crossover,
    crossunder,
)
from alphaedge.modules.strategy.domain.value_objects import Signal, StrategyContext
from alphaedge.shared.domain.exceptions import ValidationError

from alphaedge.modules.backtesting.domain.sandbox import (
    apply_memory_limit_mb,
    run_with_timeout,
)

_ALLOWED_IMPORT_PREFIXES = ("alphaedge.modules.strategy.domain",)


def _restricted_import(
    name: str,
    globals: dict[str, object] | None = None,
    locals: dict[str, object] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> object:
    if level != 0:
        raise ImportError("relative imports are not allowed in strategies")
    if not any(
        name == prefix or name.startswith(f"{prefix}.") for prefix in _ALLOWED_IMPORT_PREFIXES
    ):
        raise ImportError(f"import of module '{name}' is not allowed")
    return builtins.__import__(name, globals, locals, list(fromlist), level)


def _safe_builtins() -> dict[str, object]:
    allowed = {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "len",
        "list",
        "max",
        "min",
        "range",
        "str",
        "sum",
        "tuple",
        "staticmethod",
        "classmethod",
        "property",
        "super",
        "isinstance",
        "issubclass",
        "True",
        "False",
        "None",
        "__build_class__",
        "__name__",
    }
    out: dict[str, object] = {"Decimal": Decimal, "__import__": _restricted_import}
    for name in allowed:
        if hasattr(builtins, name):
            out[name] = getattr(builtins, name)
    return out


def _strategy_namespace() -> dict[str, object]:
    from alphaedge.modules.strategy.domain import Signal as DomainSignal
    from alphaedge.modules.strategy.domain import SignalAction as DomainSignalAction
    from alphaedge.modules.strategy.domain import StrategyBase as DomainStrategyBase
    from alphaedge.modules.strategy.domain import StrategyContext as DomainStrategyContext

    return {
        "Decimal": Decimal,
        "Signal": DomainSignal,
        "SignalAction": DomainSignalAction,
        "StrategyBase": DomainStrategyBase,
        "StrategyContext": DomainStrategyContext,
        "SMA": SMA,
        "EMA": EMA,
        "RSI": RSI,
        "MACD": MACD,
        "BollingerBands": BollingerBands,
        "create_indicator": create_indicator,
        "crossover": crossover,
        "crossunder": crossunder,
    }


def load_python_strategy(source_code: str) -> type[StrategyBase]:
    """Load a user-defined StrategyBase subclass from source in a restricted namespace."""
    from alphaedge.config import settings
    from alphaedge.modules.strategy.domain.dsl import StrategyCompiler

    StrategyCompiler.validate_python(source_code)
    if "StrategyBase" not in source_code:
        raise ValidationError("Python strategy must subclass StrategyBase")

    apply_memory_limit_mb()

    def _load() -> type[StrategyBase]:
        namespace: dict[str, object] = _strategy_namespace()
        namespace["__builtins__"] = _safe_builtins()
        exec(compile(source_code, "<strategy>", "exec"), namespace)

        candidates: list[type[StrategyBase]] = []
        for obj in namespace.values():
            if isinstance(obj, type) and issubclass(obj, StrategyBase) and obj is not StrategyBase:
                candidates.append(obj)

        if not candidates:
            tree = ast.parse(source_code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    raise ValidationError(f"Class '{node.name}' must subclass StrategyBase")
            raise ValidationError("No StrategyBase subclass found in Python strategy")

        if len(candidates) > 1:
            raise ValidationError("Python strategy must define exactly one StrategyBase subclass")

        return candidates[0]

    return run_with_timeout(
        _load,
        seconds=settings.strategy_load_timeout_seconds,
        label="load",
    )


class PythonStrategyExecutor:
    """Runtime executor for validated Python strategies during backtesting."""

    def __init__(self, source_code: str, parameters: dict[str, object]) -> None:
        strategy_cls = load_python_strategy(source_code)
        self._strategy = strategy_cls()
        self._parameters = dict(parameters)
        self._contexts: dict[UUID, StrategyContext] = {}
        self._initialized = False

    def _context_for(self, instrument_id: UUID) -> StrategyContext:
        return self._contexts.setdefault(
            instrument_id,
            StrategyContext(parameters=self._parameters),
        )

    def on_init(self) -> None:
        if self._initialized:
            return
        from alphaedge.config import settings

        ctx = StrategyContext(parameters=self._parameters)

        def _init() -> None:
            self._strategy.on_init(ctx)

        run_with_timeout(_init, seconds=settings.strategy_exec_timeout_seconds, label="on_init")
        self._initialized = True

    def on_bar(self, bar: Bar) -> Signal | None:
        from alphaedge.config import settings

        self.on_init()
        ctx = self._context_for(bar.instrument_id)

        def _eval() -> Signal | None:
            return self._strategy.on_bar(bar, ctx)

        signal = run_with_timeout(
            _eval, seconds=settings.strategy_exec_timeout_seconds, label="on_bar"
        )
        if signal is None:
            return None
        if signal.action == SignalAction.HOLD:
            return None
        return signal

    def on_stop(self) -> None:
        for ctx in self._contexts.values():
            self._strategy.on_stop(ctx)
