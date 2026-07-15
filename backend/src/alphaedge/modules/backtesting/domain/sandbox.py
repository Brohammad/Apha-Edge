"""Resource limits and wall-clock timeouts for Python strategy execution.

Trust model (v1 — single-tenant / trusted authors):
  - AST import allowlist + restricted builtins (existing)
  - Wall-clock timeout per strategy load and per on_bar
  - Soft memory ceiling via resource.RLIMIT_AS when the OS supports it
  - Marketplace publish of Python strategies is blocked

Multi-tenant path (documented, not implemented):
  - Run each backtest in a short-lived container / Firecracker microVM
  - No network, read-only rootfs, cgroup CPU/memory, seccomp
"""

from __future__ import annotations

import resource
import signal
from collections.abc import Callable
from contextlib import contextmanager
from typing import Iterator, TypeVar

from alphaedge.config import settings
from alphaedge.shared.domain.exceptions import ValidationError

T = TypeVar("T")


class StrategyTimeoutError(ValidationError):
    """Raised when a Python strategy exceeds its wall-clock budget."""


def apply_memory_limit_mb(limit_mb: int | None = None) -> None:
    """Best-effort address-space soft limit (ignored on platforms without RLIMIT_AS)."""
    mb = limit_mb if limit_mb is not None else settings.strategy_memory_limit_mb
    if mb <= 0:
        return
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        ceiling = mb * 1024 * 1024
        # Never raise the hard limit; only tighten soft when possible.
        new_soft = min(ceiling, hard) if hard > 0 else ceiling
        if soft == resource.RLIM_INFINITY or soft > new_soft:
            resource.setrlimit(resource.RLIMIT_AS, (new_soft, hard))
    except (ValueError, OSError, AttributeError):
        return


@contextmanager
def wall_clock_timeout(seconds: float, *, label: str = "strategy") -> Iterator[None]:
    """Unix SIGALRM wall-clock timeout. No-op when seconds <= 0 or signals unavailable."""
    if seconds <= 0:
        yield
        return

    def _handler(_signum: int, _frame: object) -> None:
        raise StrategyTimeoutError(
            f"Python strategy {label} exceeded {seconds:.1f}s wall-clock limit"
        )

    previous = None
    try:
        previous = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    except AttributeError:
        # Windows / restricted environments — skip timer.
        yield
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
        except AttributeError:
            pass
        if previous is not None:
            signal.signal(signal.SIGALRM, previous)


def run_with_timeout(fn: Callable[[], T], *, seconds: float, label: str) -> T:
    with wall_clock_timeout(seconds, label=label):
        return fn()
