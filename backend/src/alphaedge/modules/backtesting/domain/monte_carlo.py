"""Monte Carlo and stress test simulations."""

from __future__ import annotations

import random
from decimal import Decimal


def monte_carlo_paths(
    *,
    start_equity: Decimal,
    mu: float,
    sigma: float,
    days: int,
    simulations: int,
) -> list[list[float]]:
    paths: list[list[float]] = []
    start = float(start_equity)
    for _ in range(simulations):
        equity = start
        path = [equity]
        for _d in range(days):
            shock = random.gauss(mu, sigma)
            equity *= 1.0 + shock
            path.append(equity)
        paths.append(path)
    return paths


def stress_test_drawdown(paths: list[list[float]]) -> dict[str, float]:
    max_dds = []
    for path in paths:
        peak = path[0]
        worst = 0.0
        for v in path:
            peak = max(peak, v)
            dd = (v - peak) / peak if peak else 0.0
            worst = min(worst, dd)
        max_dds.append(worst)
    return {
        "p95_drawdown": sorted(max_dds)[int(len(max_dds) * 0.05)] if max_dds else 0.0,
        "median_drawdown": sorted(max_dds)[len(max_dds) // 2] if max_dds else 0.0,
    }
