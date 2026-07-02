from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.portfolio.domain.enums import RiskLimitType
from alphaedge.modules.risk.domain.entities import RiskLimit, RiskSnapshot
from alphaedge.modules.risk.domain.repositories import RiskLimitRepository, RiskSnapshotRepository
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskSnapshotModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "risk_snapshots"

    portfolio_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    var_95: Mapped[Decimal | None] = mapped_column(nullable=True)
    var_99: Mapped[Decimal | None] = mapped_column(nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(nullable=True)
    sortino_ratio: Mapped[Decimal | None] = mapped_column(nullable=True)
    beta: Mapped[Decimal | None] = mapped_column(nullable=True)
    alpha: Mapped[Decimal | None] = mapped_column(nullable=True)
    volatility: Mapped[Decimal | None] = mapped_column(nullable=True)
    correlation_matrix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RiskLimitModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "risk_limits"

    portfolio_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    limit_type: Mapped[str] = mapped_column(nullable=False)
    threshold: Mapped[Decimal] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)


def _snapshot_to_entity(m: RiskSnapshotModel) -> RiskSnapshot:
    return RiskSnapshot(
        id=m.id,
        portfolio_id=m.portfolio_id,
        snapshot_at=m.snapshot_at,
        var_95=m.var_95,
        var_99=m.var_99,
        max_drawdown=m.max_drawdown,
        sharpe_ratio=m.sharpe_ratio,
        sortino_ratio=m.sortino_ratio,
        beta=m.beta,
        alpha=m.alpha,
        volatility=m.volatility,
        correlation_matrix=m.correlation_matrix,
        metrics=m.metrics,
    )


def _limit_to_entity(m: RiskLimitModel) -> RiskLimit:
    return RiskLimit(
        id=m.id,
        portfolio_id=m.portfolio_id,
        limit_type=RiskLimitType(m.limit_type),
        threshold=m.threshold,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyRiskSnapshotRepository(RiskSnapshotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, snapshot: RiskSnapshot) -> RiskSnapshot:
        model = RiskSnapshotModel(
            id=snapshot.id,
            portfolio_id=snapshot.portfolio_id,
            snapshot_at=snapshot.snapshot_at,
            var_95=snapshot.var_95,
            var_99=snapshot.var_99,
            max_drawdown=snapshot.max_drawdown,
            sharpe_ratio=snapshot.sharpe_ratio,
            sortino_ratio=snapshot.sortino_ratio,
            beta=snapshot.beta,
            alpha=snapshot.alpha,
            volatility=snapshot.volatility,
            correlation_matrix=snapshot.correlation_matrix,
            metrics=snapshot.metrics,
        )
        self._session.add(model)
        await self._session.flush()
        return _snapshot_to_entity(model)

    async def get_by_id(self, snapshot_id: UUID) -> RiskSnapshot | None:
        model = await self._session.get(RiskSnapshotModel, snapshot_id)
        return _snapshot_to_entity(model) if model else None

    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> list[RiskSnapshot]:
        stmt = (
            select(RiskSnapshotModel)
            .where(RiskSnapshotModel.portfolio_id == portfolio_id)
            .order_by(RiskSnapshotModel.snapshot_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_snapshot_to_entity(m) for m in result.scalars().all()]

    async def get_latest(self, portfolio_id: UUID) -> RiskSnapshot | None:
        stmt = (
            select(RiskSnapshotModel)
            .where(RiskSnapshotModel.portfolio_id == portfolio_id)
            .order_by(RiskSnapshotModel.snapshot_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _snapshot_to_entity(model) if model else None


class SQLAlchemyRiskLimitRepository(RiskLimitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, limit: RiskLimit) -> RiskLimit:
        model = RiskLimitModel(
            id=limit.id,
            portfolio_id=limit.portfolio_id,
            limit_type=limit.limit_type.value,
            threshold=limit.threshold,
            is_active=limit.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return _limit_to_entity(model)

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RiskLimit]:
        stmt = select(RiskLimitModel).where(RiskLimitModel.portfolio_id == portfolio_id)
        result = await self._session.execute(stmt)
        return [_limit_to_entity(m) for m in result.scalars().all()]

    async def upsert(self, limit: RiskLimit) -> RiskLimit:
        existing = await self.get_by_portfolio_and_type(limit.portfolio_id, limit.limit_type.value)
        if existing:
            model = await self._session.get(RiskLimitModel, existing.id)
            assert model is not None
            model.threshold = limit.threshold
            model.is_active = limit.is_active
            model.updated_at = datetime.now(UTC)
            await self._session.flush()
            return _limit_to_entity(model)
        return await self.save(limit)

    async def get_by_portfolio_and_type(
        self, portfolio_id: UUID, limit_type: str
    ) -> RiskLimit | None:
        stmt = select(RiskLimitModel).where(
            RiskLimitModel.portfolio_id == portfolio_id,
            RiskLimitModel.limit_type == limit_type,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _limit_to_entity(model) if model else None
