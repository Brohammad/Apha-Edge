"""Liquidity and leverage pre-trade checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LiquidityResult:
    allowed: bool
    reason: str | None = None


def check_liquidity(
    *,
    order_notional: Decimal,
    avg_daily_volume_notional: Decimal,
    max_participation_pct: Decimal = Decimal("0.05"),
) -> LiquidityResult:
    if avg_daily_volume_notional <= 0:
        return LiquidityResult(allowed=True)
    participation = order_notional / avg_daily_volume_notional
    if participation > max_participation_pct:
        return LiquidityResult(
            allowed=False,
            reason=f"Order is {participation:.2%} of ADV (limit {max_participation_pct:.2%})",
        )
    return LiquidityResult(allowed=True)


def check_leverage(
    *,
    gross_exposure: Decimal,
    equity: Decimal,
    max_leverage: Decimal,
) -> LiquidityResult:
    if equity <= 0:
        return LiquidityResult(allowed=False, reason="Non-positive equity")
    leverage = gross_exposure / equity
    if leverage > max_leverage:
        return LiquidityResult(
            allowed=False,
            reason=f"Leverage {leverage:.2f}x exceeds limit {max_leverage:.2f}x",
        )
    return LiquidityResult(allowed=True)
