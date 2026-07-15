"""Strategy execution runners — in-process (default) and subprocess isolation.

Marketplace Python publish stays blocked until a container runner is enabled.
``STRATEGY_RUNNER_MODE=subprocess`` evaluates Python strategies in a child
process with a hard join timeout (stronger than in-thread SIGALRM alone).
"""

from __future__ import annotations

import multiprocessing as mp
from abc import ABC, abstractmethod
from typing import Any

from alphaedge.config import settings
from alphaedge.modules.backtesting.domain.python_executor import PythonStrategyExecutor
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.value_objects import Signal
from alphaedge.shared.domain.exceptions import ValidationError


class StrategyRunner(ABC):
    @abstractmethod
    def on_bar(self, bar: Bar) -> Signal | None: ...

    @abstractmethod
    def on_stop(self) -> None: ...


class InProcessStrategyRunner(StrategyRunner):
    def __init__(self, source_code: str, parameters: dict[str, object]) -> None:
        self._executor = PythonStrategyExecutor(source_code, parameters)

    def on_bar(self, bar: Bar) -> Signal | None:
        return self._executor.on_bar(bar)

    def on_stop(self) -> None:
        self._executor.on_stop()


def _bar_to_payload(bar: Bar) -> dict[str, Any]:
    return {
        "instrument_id": str(bar.instrument_id),
        "timeframe": bar.timeframe.value,
        "timestamp": bar.timestamp.isoformat(),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
        "source": bar.source,
    }


def _payload_to_bar(bar_payload: dict[str, Any]) -> Bar:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID as _UUID

    from alphaedge.modules.market_data.domain.enums import Timeframe

    return Bar(
        instrument_id=_UUID(bar_payload["instrument_id"]),
        timeframe=Timeframe(bar_payload["timeframe"]),
        timestamp=datetime.fromisoformat(bar_payload["timestamp"]),
        open=Decimal(bar_payload["open"]),
        high=Decimal(bar_payload["high"]),
        low=Decimal(bar_payload["low"]),
        close=Decimal(bar_payload["close"]),
        volume=Decimal(bar_payload["volume"]),
        source=bar_payload.get("source", "mock"),
    )


def _signal_to_payload(signal: Signal | None) -> dict[str, Any] | None:
    if signal is None:
        return None
    return {
        "action": signal.action.value,
        "reason": signal.reason,
        "strength": signal.strength,
        "stop_loss_pct": signal.stop_loss_pct,
        "take_profit_pct": signal.take_profit_pct,
    }


def _payload_to_signal(raw: dict[str, Any] | None) -> Signal | None:
    if raw is None:
        return None
    from alphaedge.modules.strategy.domain.enums import SignalAction

    return Signal(
        action=SignalAction(raw["action"]),
        reason=str(raw.get("reason") or ""),
        strength=raw.get("strength"),
        stop_loss_pct=raw.get("stop_loss_pct"),
        take_profit_pct=raw.get("take_profit_pct"),
    )


def _worker_loop(
    source_code: str,
    parameters: dict[str, Any],
    in_q: mp.Queue,
    out_q: mp.Queue,
) -> None:
    import contextlib

    try:
        executor = PythonStrategyExecutor(source_code, parameters)
    except Exception as exc:  # noqa: BLE001
        out_q.put({"ok": False, "error": f"load failed: {exc}"})
        return
    out_q.put({"ok": True, "ready": True})
    while True:
        msg = in_q.get()
        if not msg or msg.get("cmd") == "stop":
            with contextlib.suppress(Exception):
                executor.on_stop()
            out_q.put({"ok": True, "stopped": True})
            return
        if msg.get("cmd") == "bar":
            try:
                signal = executor.on_bar(_payload_to_bar(msg["bar"]))
                out_q.put({"ok": True, "signal": _signal_to_payload(signal)})
            except Exception as exc:  # noqa: BLE001
                out_q.put({"ok": False, "error": str(exc)})


class SubprocessStrategyRunner(StrategyRunner):
    """Long-lived child process evaluating bars with hard join timeouts."""

    def __init__(self, source_code: str, parameters: dict[str, object]) -> None:
        self._timeout = max(settings.strategy_exec_timeout_seconds, 1.0)
        self._load_timeout = max(settings.strategy_load_timeout_seconds, 1.0)
        ctx = mp.get_context("spawn")
        self._in_q: mp.Queue = ctx.Queue()
        self._out_q: mp.Queue = ctx.Queue()
        self._proc = ctx.Process(
            target=_worker_loop,
            args=(source_code, dict(parameters), self._in_q, self._out_q),
        )
        self._proc.start()
        ready = self._recv(self._load_timeout)
        if not ready.get("ok"):
            self.on_stop()
            raise ValidationError(ready.get("error") or "Strategy subprocess failed to start")

    def _recv(self, timeout: float) -> dict[str, Any]:
        try:
            return self._out_q.get(timeout=timeout)
        except Exception as exc:
            if self._proc.is_alive():
                self._proc.terminate()
                self._proc.join(timeout=1.0)
            raise ValidationError(
                f"Python strategy subprocess timed out after {timeout}s"
            ) from exc

    def on_bar(self, bar: Bar) -> Signal | None:
        if not self._proc.is_alive():
            raise ValidationError("Python strategy subprocess is not running")
        self._in_q.put({"cmd": "bar", "bar": _bar_to_payload(bar)})
        result = self._recv(self._timeout)
        if not result.get("ok"):
            raise ValidationError(result.get("error") or "Strategy subprocess bar failed")
        return _payload_to_signal(result.get("signal"))

    def on_stop(self) -> None:
        if self._proc.is_alive():
            try:
                self._in_q.put({"cmd": "stop"})
                self._proc.join(timeout=self._timeout)
            except Exception:
                pass
            if self._proc.is_alive():
                self._proc.terminate()
                self._proc.join(timeout=1.0)


def create_strategy_runner(
    source_code: str,
    parameters: dict[str, object],
    *,
    mode: str | None = None,
) -> StrategyRunner:
    selected = (mode or settings.strategy_runner_mode).lower()
    if selected == "subprocess":
        return SubprocessStrategyRunner(source_code, parameters)
    return InProcessStrategyRunner(source_code, parameters)
