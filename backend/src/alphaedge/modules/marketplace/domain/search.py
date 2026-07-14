"""Marketplace search, filters, and ratings."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyRating:
    strategy_id: str
    avg_rating: Decimal
    review_count: int


def search_strategies(
    items: list[dict],
    *,
    query: str = "",
    min_rating: float = 0.0,
    tags: list[str] | None = None,
) -> list[dict]:
    q = query.lower()
    tags = tags or []
    out = []
    for item in items:
        if q and q not in item.get("name", "").lower() and q not in item.get("description", "").lower():
            continue
        if float(item.get("avg_rating", 0)) < min_rating:
            continue
        if tags and not set(tags).intersection(set(item.get("tags", []))):
            continue
        out.append(item)
    return out
