from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio, RebalancePlan
from alphaedge.modules.portfolio.domain.enums import RebalanceStatus
from alphaedge.modules.portfolio.domain.repositories import (
    HoldingRepository,
    PortfolioRepository,
    RebalancePlanRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PortfolioModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "portfolios"

    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    base_currency: Mapped[str] = mapped_column(default="USD")
    initial_capital: Mapped[Decimal] = mapped_column(nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(nullable=False)
    is_paper: Mapped[bool] = mapped_column(default=True)


class HoldingModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "holdings"

    portfolio_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(nullable=False)
    current_price: Mapped[Decimal] = mapped_column(nullable=False)
    market_value: Mapped[Decimal] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RebalancePlanModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "rebalance_plans"

    portfolio_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    target_allocation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    proposed_trades: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(default=RebalanceStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _portfolio_to_entity(m: PortfolioModel) -> Portfolio:
    return Portfolio(
        id=m.id,
        user_id=m.user_id,
        name=m.name,
        base_currency=m.base_currency,
        initial_capital=m.initial_capital,
        cash_balance=m.cash_balance,
        is_paper=m.is_paper,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _holding_to_entity(m: HoldingModel) -> Holding:
    return Holding(
        id=m.id,
        portfolio_id=m.portfolio_id,
        instrument_id=m.instrument_id,
        quantity=m.quantity,
        avg_cost=m.avg_cost,
        current_price=m.current_price,
        market_value=m.market_value,
        updated_at=m.updated_at,
    )


def _plan_to_entity(m: RebalancePlanModel) -> RebalancePlan:
    return RebalancePlan(
        id=m.id,
        portfolio_id=m.portfolio_id,
        target_allocation=m.target_allocation,
        proposed_trades=m.proposed_trades,
        status=RebalanceStatus(m.status),
        created_at=m.created_at,
    )


class SQLAlchemyPortfolioRepository(PortfolioRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, portfolio: Portfolio) -> Portfolio:
        model = PortfolioModel(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            base_currency=portfolio.base_currency,
            initial_capital=portfolio.initial_capital,
            cash_balance=portfolio.cash_balance,
            is_paper=portfolio.is_paper,
        )
        self._session.add(model)
        await self._session.flush()
        return _portfolio_to_entity(model)

    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        model = await self._session.get(PortfolioModel, portfolio_id)
        return _portfolio_to_entity(model) if model else None

    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Portfolio]:
        stmt = (
            select(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
            .order_by(PortfolioModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_portfolio_to_entity(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(PortfolioModel)
            .where(PortfolioModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update(self, portfolio: Portfolio) -> Portfolio:
        model = await self._session.get(PortfolioModel, portfolio.id)
        if not model:
            raise ValueError(f"Portfolio {portfolio.id} not found")
        model.cash_balance = portfolio.cash_balance
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _portfolio_to_entity(model)


class SQLAlchemyHoldingRepository(HoldingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, holding: Holding) -> Holding:
        model = HoldingModel(
            id=holding.id,
            portfolio_id=holding.portfolio_id,
            instrument_id=holding.instrument_id,
            quantity=holding.quantity,
            avg_cost=holding.avg_cost,
            current_price=holding.current_price,
            market_value=holding.market_value,
            updated_at=holding.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _holding_to_entity(model)

    async def get_by_portfolio_and_instrument(
        self, portfolio_id: UUID, instrument_id: UUID
    ) -> Holding | None:
        stmt = select(HoldingModel).where(
            HoldingModel.portfolio_id == portfolio_id,
            HoldingModel.instrument_id == instrument_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _holding_to_entity(model) if model else None

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[Holding]:
        stmt = select(HoldingModel).where(HoldingModel.portfolio_id == portfolio_id)
        result = await self._session.execute(stmt)
        return [_holding_to_entity(m) for m in result.scalars().all()]

    async def upsert(self, holding: Holding) -> Holding:
        existing = await self.get_by_portfolio_and_instrument(
            holding.portfolio_id, holding.instrument_id
        )
        if existing:
            model = await self._session.get(HoldingModel, existing.id)
            assert model is not None
            model.quantity = holding.quantity
            model.avg_cost = holding.avg_cost
            model.current_price = holding.current_price
            model.market_value = holding.market_value
            model.updated_at = holding.updated_at
            await self._session.flush()
            return _holding_to_entity(model)
        return await self.save(holding)

    async def delete(self, holding_id: UUID) -> None:
        model = await self._session.get(HoldingModel, holding_id)
        if model:
            await self._session.delete(model)


class SQLAlchemyRebalancePlanRepository(RebalancePlanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, plan: RebalancePlan) -> RebalancePlan:
        model = RebalancePlanModel(
            id=plan.id,
            portfolio_id=plan.portfolio_id,
            target_allocation=plan.target_allocation,
            proposed_trades=plan.proposed_trades,
            status=plan.status.value,
            created_at=plan.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _plan_to_entity(model)

    async def get_by_id(self, plan_id: UUID) -> RebalancePlan | None:
        model = await self._session.get(RebalancePlanModel, plan_id)
        return _plan_to_entity(model) if model else None

    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> list[RebalancePlan]:
        stmt = (
            select(RebalancePlanModel)
            .where(RebalancePlanModel.portfolio_id == portfolio_id)
            .order_by(RebalancePlanModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_plan_to_entity(m) for m in result.scalars().all()]
