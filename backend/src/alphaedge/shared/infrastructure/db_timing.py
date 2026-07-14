"""Observe database operation latency for Prometheus."""

import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from alphaedge.shared.infrastructure.metrics import DB_QUERY_LATENCY

P = ParamSpec("P")
T = TypeVar("T")


def observe_db(operation: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for async repository methods."""

    def decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                DB_QUERY_LATENCY.labels(operation=operation).observe(time.perf_counter() - start)

        return wrapper

    return decorator
