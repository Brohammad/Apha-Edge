"""Portfolio-level strategy type."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class PortfolioStrategy:
    id: UUID
    portfolio_id: UUID
    name: str
    target_weights: dict[str, Decimal] = field(default_factory=dict)
    rebalance_threshold: Decimal = Decimal("0.05")
    is_active: bool = True

    @staticmethod
    def create(portfolio_id: UUID, name: str, weights: dict[str, Decimal]) -> "PortfolioStrategy":
        return PortfolioStrategy(
            id=uuid4(),
            portfolio_id=portfolio_id,
            name=name,
            target_weights=weights,
        )

    def needs_rebalance(self, current_weights: dict[str, Decimal]) -> bool:
        for symbol, target in self.target_weights.items():
            current = current_weights.get(symbol, Decimal("0"))
            if abs(current - target) > self.rebalance_threshold:
                return True
        return False
