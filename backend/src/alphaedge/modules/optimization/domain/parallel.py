"""Parallel backtest grid optimization."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable


def run_parallel_grid(
    jobs: list[dict[str, Any]],
    worker: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    if not jobs:
        return []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(worker, jobs))
