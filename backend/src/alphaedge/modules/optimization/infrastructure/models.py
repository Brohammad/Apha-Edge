from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.optimization.domain.entities import OptimizationRun, OptimizationTrial
from alphaedge.modules.optimization.domain.enums import (
    OptimizationMethod,
    OptimizationObjective,
    OptimizationStatus,
    TrialStatus,
)
from alphaedge.modules.optimization.domain.repositories import (
    OptimizationRunRepository,
    OptimizationTrialRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OptimizationRunModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "optimization_runs"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    strategy_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    method: Mapped[str] = mapped_column(nullable=False)
    objective: Mapped[str] = mapped_column(nullable=False)
    parameter_space: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    backtest_config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    walk_forward_config: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(default=OptimizationStatus.QUEUED.value, index=True)
    best_trial_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    total_trials: Mapped[int] = mapped_column(default=0)
    completed_trials: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(nullable=True)


class OptimizationTrialModel(Base):
    __tablename__ = "optimization_trials"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    optimization_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    backtest_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    objective_value: Mapped[Decimal | None] = mapped_column(nullable=True)
    in_sample_objective: Mapped[Decimal | None] = mapped_column(nullable=True)
    window_index: Mapped[int | None] = mapped_column(nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default=TrialStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


def _run_to_entity(model: OptimizationRunModel) -> OptimizationRun:
    return OptimizationRun(
        id=model.id,
        user_id=model.user_id,
        strategy_version_id=model.strategy_version_id,
        name=model.name,
        method=OptimizationMethod(model.method),
        objective=OptimizationObjective(model.objective),
        parameter_space=model.parameter_space,
        backtest_config=model.backtest_config,
        walk_forward_config=model.walk_forward_config,
        status=OptimizationStatus(model.status),
        best_trial_id=model.best_trial_id,
        total_trials=model.total_trials,
        completed_trials=model.completed_trials,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
        celery_task_id=model.celery_task_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _trial_to_entity(model: OptimizationTrialModel) -> OptimizationTrial:
    return OptimizationTrial(
        id=model.id,
        optimization_run_id=model.optimization_run_id,
        parameters=model.parameters,
        status=TrialStatus(model.status),
        backtest_run_id=model.backtest_run_id,
        objective_value=model.objective_value,
        in_sample_objective=model.in_sample_objective,
        window_index=model.window_index,
        rank=model.rank,
        created_at=model.created_at,
    )


class SQLAlchemyOptimizationRunRepository(OptimizationRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: OptimizationRun) -> OptimizationRun:
        model = OptimizationRunModel(
            id=run.id,
            user_id=run.user_id,
            strategy_version_id=run.strategy_version_id,
            name=run.name,
            method=run.method.value,
            objective=run.objective.value,
            parameter_space=run.parameter_space,
            backtest_config=run.backtest_config,
            walk_forward_config=run.walk_forward_config,
            status=run.status.value,
            best_trial_id=run.best_trial_id,
            total_trials=run.total_trials,
            completed_trials=run.completed_trials,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            celery_task_id=run.celery_task_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _run_to_entity(model)

    async def get_by_id(self, run_id: UUID) -> OptimizationRun | None:
        model = await self._session.get(OptimizationRunModel, run_id)
        return _run_to_entity(model) if model else None

    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[OptimizationRun]:
        stmt = (
            select(OptimizationRunModel)
            .where(OptimizationRunModel.user_id == user_id)
            .order_by(OptimizationRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_run_to_entity(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OptimizationRunModel)
            .where(OptimizationRunModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update(self, run: OptimizationRun) -> OptimizationRun:
        model = await self._session.get(OptimizationRunModel, run.id)
        if not model:
            raise ValueError(f"OptimizationRun {run.id} not found")
        model.status = run.status.value
        model.best_trial_id = run.best_trial_id
        model.total_trials = run.total_trials
        model.completed_trials = run.completed_trials
        model.started_at = run.started_at
        model.completed_at = run.completed_at
        model.error_message = run.error_message
        model.celery_task_id = run.celery_task_id
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _run_to_entity(model)


class SQLAlchemyOptimizationTrialRepository(OptimizationTrialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trial: OptimizationTrial) -> OptimizationTrial:
        model = OptimizationTrialModel(
            id=trial.id,
            optimization_run_id=trial.optimization_run_id,
            backtest_run_id=trial.backtest_run_id,
            parameters=trial.parameters,
            objective_value=trial.objective_value,
            in_sample_objective=trial.in_sample_objective,
            window_index=trial.window_index,
            rank=trial.rank,
            status=trial.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        return _trial_to_entity(model)

    async def save_many(self, trials: list[OptimizationTrial]) -> list[OptimizationTrial]:
        saved: list[OptimizationTrial] = []
        for trial in trials:
            saved.append(await self.save(trial))
        return saved

    async def get_by_id(self, trial_id: UUID) -> OptimizationTrial | None:
        model = await self._session.get(OptimizationTrialModel, trial_id)
        return _trial_to_entity(model) if model else None

    async def list_by_run_id(self, run_id: UUID) -> list[OptimizationTrial]:
        stmt = (
            select(OptimizationTrialModel)
            .where(OptimizationTrialModel.optimization_run_id == run_id)
            .order_by(
                OptimizationTrialModel.rank.asc().nullslast(),
                OptimizationTrialModel.created_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return [_trial_to_entity(m) for m in result.scalars().all()]

    async def update(self, trial: OptimizationTrial) -> OptimizationTrial:
        model = await self._session.get(OptimizationTrialModel, trial.id)
        if not model:
            raise ValueError(f"OptimizationTrial {trial.id} not found")
        model.backtest_run_id = trial.backtest_run_id
        model.objective_value = trial.objective_value
        model.in_sample_objective = trial.in_sample_objective
        model.rank = trial.rank
        model.status = trial.status.value
        await self._session.flush()
        return _trial_to_entity(model)

    async def update_many(self, trials: list[OptimizationTrial]) -> None:
        for trial in trials:
            await self.update(trial)
