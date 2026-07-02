from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.portfolio.domain.enums import RebalanceStatus
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class Portfolio:
    id: UUID
    user_id: UUID
    name: str
    base_currency: str
    initial_capital: Decimal
    cash_balance: Decimal
    is_paper: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        name: str,
        initial_capital: Decimal,
        *,
        base_currency: str = "USD",
        is_paper: bool = True,
    ) -> "Portfolio":
        name = name.strip()
        if not name:
            raise ValidationError("Portfolio name is required")
        if initial_capital <= 0:
            raise ValidationError("Initial capital must be positive")
        return Portfolio(
            id=uuid4(),
            user_id=user_id,
            name=name,
            base_currency=base_currency.upper(),
            initial_capital=initial_capital,
            cash_balance=initial_capital,
            is_paper=is_paper,
        )


@dataclass
class Holding:
    id: UUID
    portfolio_id: UUID
    instrument_id: UUID
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        portfolio_id: UUID,
        instrument_id: UUID,
        quantity: Decimal,
        avg_cost: Decimal,
        current_price: Decimal,
    ) -> "Holding":
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative")
        market_value = quantity * current_price
        return Holding(
            id=uuid4(),
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            quantity=quantity,
            avg_cost=avg_cost,
            current_price=current_price,
            market_value=market_value,
        )

    def refresh_price(self, price: Decimal) -> None:
        self.current_price = price
        self.market_value = self.quantity * price
        self.updated_at = datetime.now(UTC)


@dataclass
class RebalancePlan:
    id: UUID
    portfolio_id: UUID
    target_allocation: dict[str, float]
    proposed_trades: list[dict[str, object]]
    status: RebalanceStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        portfolio_id: UUID,
        target_allocation: dict[str, float],
        proposed_trades: list[dict[str, object]],
    ) -> "RebalancePlan":
        if not target_allocation:
            raise ValidationError("Target allocation is required")
        total = sum(target_allocation.values())
        if abs(total - 1.0) > 0.01:
            raise ValidationError("Target allocation weights must sum to ~1.0")
        return RebalancePlan(
            id=uuid4(),
            portfolio_id=portfolio_id,
            target_allocation=target_allocation,
            proposed_trades=proposed_trades,
            status=RebalanceStatus.DRAFT,
        )
