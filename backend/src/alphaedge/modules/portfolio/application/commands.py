from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio, RebalancePlan


@dataclass(frozen=True)
class CreatePortfolioCommand:
    user_id: UUID
    name: str
    initial_capital: Decimal
    base_currency: str = "USD"
    is_paper: bool = True


@dataclass(frozen=True)
class ListPortfoliosQuery:
    user_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetPortfolioQuery:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class GetHoldingsQuery:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class GetPerformanceQuery:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class GenerateRebalanceCommand:
    user_id: UUID
    portfolio_id: UUID
    target_allocation: dict[str, float]


@dataclass(frozen=True)
class GetRebalancePlanQuery:
    user_id: UUID
    portfolio_id: UUID
    plan_id: UUID


@dataclass(frozen=True)
class SyncFromBacktestCommand:
    user_id: UUID
    portfolio_id: UUID
    backtest_run_id: UUID


@dataclass(frozen=True)
class PortfolioDTO:
    id: UUID
    user_id: UUID
    name: str
    base_currency: str
    initial_capital: str
    cash_balance: str
    is_paper: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: Portfolio) -> "PortfolioDTO":
        return PortfolioDTO(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name,
            base_currency=entity.base_currency,
            initial_capital=str(entity.initial_capital),
            cash_balance=str(entity.cash_balance),
            is_paper=entity.is_paper,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class HoldingDTO:
    id: UUID
    portfolio_id: UUID
    instrument_id: UUID
    quantity: str
    avg_cost: str
    current_price: str
    market_value: str
    updated_at: datetime

    @staticmethod
    def from_entity(entity: Holding) -> "HoldingDTO":
        return HoldingDTO(
            id=entity.id,
            portfolio_id=entity.portfolio_id,
            instrument_id=entity.instrument_id,
            quantity=str(entity.quantity),
            avg_cost=str(entity.avg_cost),
            current_price=str(entity.current_price),
            market_value=str(entity.market_value),
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class RebalancePlanDTO:
    id: UUID
    portfolio_id: UUID
    target_allocation: dict[str, float]
    proposed_trades: list[dict[str, object]]
    status: str
    created_at: datetime

    @staticmethod
    def from_entity(entity: RebalancePlan) -> "RebalancePlanDTO":
        return RebalancePlanDTO(
            id=entity.id,
            portfolio_id=entity.portfolio_id,
            target_allocation=entity.target_allocation,
            proposed_trades=entity.proposed_trades,
            status=entity.status.value,
            created_at=entity.created_at,
        )
