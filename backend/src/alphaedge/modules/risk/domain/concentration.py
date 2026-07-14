"""Position concentration and sector limit checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ConcentrationResult:
    allowed: bool
    reason: str | None = None


def check_sector_limit(
    *,
    sector_weights: dict[str, Decimal],
    sector: str,
    proposed_weight: Decimal,
    max_sector_pct: Decimal,
) -> ConcentrationResult:
    current = sector_weights.get(sector, Decimal("0"))
    if current + proposed_weight > max_sector_pct:
        return ConcentrationResult(
            allowed=False,
            reason=f"Sector {sector} would be {(current + proposed_weight):.2%} (limit {max_sector_pct:.2%})",
        )
    return ConcentrationResult(allowed=True)


def check_position_concentration(
    *,
    position_weight: Decimal,
    max_position_pct: Decimal,
) -> ConcentrationResult:
    if position_weight > max_position_pct:
        return ConcentrationResult(
            allowed=False,
            reason=f"Position weight {position_weight:.2%} exceeds limit {max_position_pct:.2%}",
        )
    return ConcentrationResult(allowed=True)
