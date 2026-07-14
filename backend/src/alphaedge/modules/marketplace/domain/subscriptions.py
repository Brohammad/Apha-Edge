"""Strategy subscriptions and revenue sharing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class StrategySubscription:
    id: UUID
    strategy_id: UUID
    subscriber_id: UUID
    monthly_price: Decimal
    author_share_pct: Decimal = Decimal("0.70")

    @staticmethod
    def create(strategy_id: UUID, subscriber_id: UUID, price: Decimal) -> "StrategySubscription":
        return StrategySubscription(
            id=uuid4(),
            strategy_id=strategy_id,
            subscriber_id=subscriber_id,
            monthly_price=price,
        )

    def author_payout(self) -> Decimal:
        return (self.monthly_price * self.author_share_pct).quantize(Decimal("0.01"))
