"""Volatility regime detection."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class VolatilityRegime(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


def detect_regime(returns: list[Decimal], *, low_thresh: float = 0.01, high_thresh: float = 0.03) -> VolatilityRegime:
    if len(returns) < 2:
        return VolatilityRegime.NORMAL
    mean = float(sum(returns) / len(returns))
    var = float(sum((float(r) - mean) ** 2 for r in returns) / (len(returns) - 1))
    vol = var**0.5
    if vol < low_thresh:
        return VolatilityRegime.LOW
    if vol > high_thresh:
        return VolatilityRegime.HIGH
    return VolatilityRegime.NORMAL
