from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.optimization.domain.enums import (
    OptimizationMethod,
    OptimizationObjective,
    OptimizationStatus,
    TrialStatus,
)
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class OptimizationRun:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    name: str
    method: OptimizationMethod
    objective: OptimizationObjective
    parameter_space: dict[str, object]
    backtest_config: dict[str, object]
    status: OptimizationStatus
    walk_forward_config: dict[str, object] | None = None
    best_trial_id: UUID | None = None
    total_trials: int = 0
    completed_trials: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        strategy_version_id: UUID,
        name: str,
        method: OptimizationMethod,
        objective: OptimizationObjective,
        parameter_space: dict[str, object],
        backtest_config: dict[str, object],
        walk_forward_config: dict[str, object] | None = None,
    ) -> "OptimizationRun":
        name = name.strip()
        if not name:
            raise ValidationError("Optimization run name is required")
        if not parameter_space:
            raise ValidationError("parameter_space must not be empty")
        return OptimizationRun(
            id=uuid4(),
            user_id=user_id,
            strategy_version_id=strategy_version_id,
            name=name,
            method=method,
            objective=objective,
            parameter_space=parameter_space,
            backtest_config=backtest_config,
            walk_forward_config=walk_forward_config,
            status=OptimizationStatus.QUEUED,
        )


@dataclass
class OptimizationTrial:
    id: UUID
    optimization_run_id: UUID
    parameters: dict[str, object]
    status: TrialStatus
    backtest_run_id: UUID | None = None
    objective_value: Decimal | None = None
    in_sample_objective: Decimal | None = None
    window_index: int | None = None
    rank: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        optimization_run_id: UUID,
        parameters: dict[str, object],
        *,
        window_index: int | None = None,
    ) -> "OptimizationTrial":
        return OptimizationTrial(
            id=uuid4(),
            optimization_run_id=optimization_run_id,
            parameters=parameters,
            status=TrialStatus.PENDING,
            window_index=window_index,
        )
