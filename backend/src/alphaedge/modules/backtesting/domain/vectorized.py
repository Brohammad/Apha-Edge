"""Vectorized numpy backtest execution path (skeleton)."""

from __future__ import annotations

from decimal import Decimal

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore


def vectorized_equity_curve(closes: list[Decimal], signals: list[int]) -> list[float]:
    if np is None or not closes:
        return [float(c) for c in closes]
    prices = np.array([float(c) for c in closes], dtype=np.float64)
    pos = np.array(signals, dtype=np.float64)
    returns = np.diff(prices, prepend=prices[0]) / np.maximum(prices, 1e-9)
    pnl = (pos[:-1] * returns[1:]) if len(pos) == len(prices) else pos * returns
    equity = 100_000.0 * np.cumprod(1.0 + pnl)
    return equity.tolist()
