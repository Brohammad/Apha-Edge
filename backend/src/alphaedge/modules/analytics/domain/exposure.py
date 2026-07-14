"""Sector, country, and style exposure calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExposureBreakdown:
    sector: dict[str, Decimal]
    country: dict[str, Decimal]
    style: dict[str, Decimal]


def compute_exposure(holdings: list[dict]) -> ExposureBreakdown:
    sector: dict[str, Decimal] = {}
    country: dict[str, Decimal] = {}
    style: dict[str, Decimal] = {}
    for h in holdings:
        mv = Decimal(str(h.get("market_value", 0)))
        sector[h.get("sector", "Unknown")] = sector.get(h.get("sector", "Unknown"), Decimal("0")) + mv
        country[h.get("country", "US")] = country.get(h.get("country", "US"), Decimal("0")) + mv
        style[h.get("style", "blend")] = style.get(h.get("style", "blend"), Decimal("0")) + mv
    return ExposureBreakdown(sector=sector, country=country, style=style)
