from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.strategy.domain.enums import StrategyType, VersionStatus
from alphaedge.modules.strategy.domain.repositories import (
    IndicatorRepository,
    StrategyDeploymentRepository,
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.modules.strategy.domain.deployment import StrategyDeployment
from alphaedge.modules.strategy.domain.value_objects import (
    IndicatorDefinition,
    Strategy,
    StrategyVersion,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StrategyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "strategies"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    strategy_type: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyVersionModel(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    strategy_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(nullable=False)
    source_code: Mapped[str] = mapped_column(nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    compiled_hash: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default=VersionStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class IndicatorModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "indicators"

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    parameters_schema: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    implementation: Mapped[str] = mapped_column(default="python")


class StrategyDeploymentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "strategy_deployments"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    strategy_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    portfolio_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    broker_connection_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    instrument_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    quantity: Mapped[Decimal] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_signal_action: Mapped[str | None] = mapped_column(nullable=True)


def _strategy_to_entity(model: StrategyModel) -> Strategy:
    return Strategy(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        description=model.description,
        strategy_type=StrategyType(model.strategy_type),
        is_active=model.is_active,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _version_to_entity(model: StrategyVersionModel) -> StrategyVersion:
    return StrategyVersion(
        id=model.id,
        strategy_id=model.strategy_id,
        version=model.version,
        source_code=model.source_code,
        parameters=model.parameters or {},
        compiled_hash=model.compiled_hash,
        status=VersionStatus(model.status),
        created_at=model.created_at,
    )


def _indicator_to_entity(model: IndicatorModel) -> IndicatorDefinition:
    return IndicatorDefinition(
        id=model.id,
        name=model.name,
        category=model.category,
        parameters_schema=model.parameters_schema,
        implementation=model.implementation,
    )


def _deployment_to_entity(model: StrategyDeploymentModel) -> StrategyDeployment:
    return StrategyDeployment(
        id=model.id,
        user_id=model.user_id,
        strategy_version_id=model.strategy_version_id,
        portfolio_id=model.portfolio_id,
        broker_connection_id=model.broker_connection_id,
        instrument_ids=[UUID(i) for i in (model.instrument_ids or [])],
        quantity=model.quantity,
        is_active=model.is_active,
        last_signal_at=model.last_signal_at,
        last_signal_action=model.last_signal_action,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyStrategyRepository(StrategyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, strategy: Strategy) -> Strategy:
        existing = await self._session.get(StrategyModel, strategy.id)
        if existing:
            existing.name = strategy.name
            existing.description = strategy.description
            existing.strategy_type = strategy.strategy_type.value
            existing.is_active = strategy.is_active
            existing.deleted_at = strategy.deleted_at
            existing.updated_at = datetime.now(UTC)
            model = existing
        else:
            model = StrategyModel(
                id=strategy.id,
                user_id=strategy.user_id,
                name=strategy.name,
                description=strategy.description,
                strategy_type=strategy.strategy_type.value,
                is_active=strategy.is_active,
                deleted_at=strategy.deleted_at,
            )
            self._session.add(model)
        await self._session.flush()
        return _strategy_to_entity(model)

    async def get_by_id(self, strategy_id: UUID) -> Strategy | None:
        model = await self._session.get(StrategyModel, strategy_id)
        return _strategy_to_entity(model) if model else None

    async def get_by_user_and_name(self, user_id: UUID, name: str) -> Strategy | None:
        stmt = select(StrategyModel).where(
            StrategyModel.user_id == user_id,
            StrategyModel.name == name.strip(),
            StrategyModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _strategy_to_entity(model) if model else None

    async def list_by_user(
        self, user_id: UUID, *, active_only: bool = True, limit: int = 50, offset: int = 0
    ) -> list[Strategy]:
        stmt = (
            select(StrategyModel)
            .where(StrategyModel.user_id == user_id, StrategyModel.deleted_at.is_(None))
            .order_by(StrategyModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if active_only:
            stmt = stmt.where(StrategyModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_strategy_to_entity(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID, *, active_only: bool = True) -> int:
        stmt = (
            select(func.count())
            .select_from(StrategyModel)
            .where(
                StrategyModel.user_id == user_id,
                StrategyModel.deleted_at.is_(None),
            )
        )
        if active_only:
            stmt = stmt.where(StrategyModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def soft_delete(self, strategy: Strategy) -> None:
        strategy.deleted_at = datetime.now(UTC)
        strategy.is_active = False
        await self.save(strategy)


class SQLAlchemyStrategyVersionRepository(StrategyVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, version: StrategyVersion) -> StrategyVersion:
        existing = await self._session.get(StrategyVersionModel, version.id)
        if existing:
            existing.source_code = version.source_code
            existing.parameters = version.parameters
            existing.compiled_hash = version.compiled_hash
            existing.status = version.status.value
            model = existing
        else:
            model = StrategyVersionModel(
                id=version.id,
                strategy_id=version.strategy_id,
                version=version.version,
                source_code=version.source_code,
                parameters=version.parameters,
                compiled_hash=version.compiled_hash,
                status=version.status.value,
            )
            self._session.add(model)
        await self._session.flush()
        return _version_to_entity(model)

    async def get_by_id(self, version_id: UUID) -> StrategyVersion | None:
        model = await self._session.get(StrategyVersionModel, version_id)
        return _version_to_entity(model) if model else None

    async def get_by_strategy_and_version(
        self, strategy_id: UUID, version: int
    ) -> StrategyVersion | None:
        stmt = select(StrategyVersionModel).where(
            StrategyVersionModel.strategy_id == strategy_id,
            StrategyVersionModel.version == version,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _version_to_entity(model) if model else None

    async def list_by_strategy(self, strategy_id: UUID) -> list[StrategyVersion]:
        stmt = (
            select(StrategyVersionModel)
            .where(StrategyVersionModel.strategy_id == strategy_id)
            .order_by(StrategyVersionModel.version.desc())
        )
        result = await self._session.execute(stmt)
        return [_version_to_entity(m) for m in result.scalars().all()]

    async def next_version_number(self, strategy_id: UUID) -> int:
        stmt = select(func.coalesce(func.max(StrategyVersionModel.version), 0)).where(
            StrategyVersionModel.strategy_id == strategy_id
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one()) + 1


class SQLAlchemyIndicatorRepository(IndicatorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[IndicatorDefinition]:
        stmt = select(IndicatorModel).order_by(IndicatorModel.category, IndicatorModel.name)
        result = await self._session.execute(stmt)
        return [_indicator_to_entity(m) for m in result.scalars().all()]

    async def get_by_name(self, name: str) -> IndicatorDefinition | None:
        stmt = select(IndicatorModel).where(IndicatorModel.name == name.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _indicator_to_entity(model) if model else None


class SQLAlchemyStrategyDeploymentRepository(StrategyDeploymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, deployment: StrategyDeployment) -> StrategyDeployment:
        existing = await self._session.get(StrategyDeploymentModel, deployment.id)
        instrument_ids = [str(i) for i in deployment.instrument_ids]
        if existing:
            existing.strategy_version_id = deployment.strategy_version_id
            existing.portfolio_id = deployment.portfolio_id
            existing.broker_connection_id = deployment.broker_connection_id
            existing.instrument_ids = instrument_ids
            existing.quantity = deployment.quantity
            existing.is_active = deployment.is_active
            existing.last_signal_at = deployment.last_signal_at
            existing.last_signal_action = deployment.last_signal_action
            existing.updated_at = datetime.now(UTC)
            model = existing
        else:
            model = StrategyDeploymentModel(
                id=deployment.id,
                user_id=deployment.user_id,
                strategy_version_id=deployment.strategy_version_id,
                portfolio_id=deployment.portfolio_id,
                broker_connection_id=deployment.broker_connection_id,
                instrument_ids=instrument_ids,
                quantity=deployment.quantity,
                is_active=deployment.is_active,
                last_signal_at=deployment.last_signal_at,
                last_signal_action=deployment.last_signal_action,
            )
            self._session.add(model)
        await self._session.flush()
        return _deployment_to_entity(model)

    async def get_by_id(self, deployment_id: UUID) -> StrategyDeployment | None:
        model = await self._session.get(StrategyDeploymentModel, deployment_id)
        return _deployment_to_entity(model) if model else None

    async def list_by_user(self, user_id: UUID) -> list[StrategyDeployment]:
        stmt = (
            select(StrategyDeploymentModel)
            .where(StrategyDeploymentModel.user_id == user_id)
            .order_by(StrategyDeploymentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_deployment_to_entity(m) for m in result.scalars().all()]

    async def list_active_for_instrument(self, instrument_id: UUID) -> list[StrategyDeployment]:
        iid = str(instrument_id)
        stmt = select(StrategyDeploymentModel).where(StrategyDeploymentModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        deployments = []
        for model in result.scalars().all():
            if iid in (model.instrument_ids or []):
                deployments.append(_deployment_to_entity(model))
        return deployments
