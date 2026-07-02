from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SubmitOptimizationCommand:
    user_id: UUID
    strategy_version_id: UUID
    name: str
    method: str
    objective: str
    parameter_space: dict[str, object]
    backtest_config: dict[str, object]
    walk_forward_config: dict[str, object] | None = None


@dataclass(frozen=True)
class ListOptimizationRunsQuery:
    user_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetOptimizationRunQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class ListOptimizationTrialsQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class GetBestTrialQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class OptimizationRunDTO:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    name: str
    method: str
    objective: str
    parameter_space: dict[str, object]
    backtest_config: dict[str, object]
    walk_forward_config: dict[str, object] | None
    status: str
    best_trial_id: UUID | None
    total_trials: int
    completed_trials: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "OptimizationRunDTO":
        return OptimizationRunDTO(
            id=entity.id,
            user_id=entity.user_id,
            strategy_version_id=entity.strategy_version_id,
            name=entity.name,
            method=entity.method.value,
            objective=entity.objective.value,
            parameter_space=entity.parameter_space,
            backtest_config=entity.backtest_config,
            walk_forward_config=entity.walk_forward_config,
            status=entity.status.value,
            best_trial_id=entity.best_trial_id,
            total_trials=entity.total_trials,
            completed_trials=entity.completed_trials,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            error_message=entity.error_message,
            celery_task_id=entity.celery_task_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class OptimizationTrialDTO:
    id: UUID
    optimization_run_id: UUID
    backtest_run_id: UUID | None
    parameters: dict[str, object]
    objective_value: str | None
    in_sample_objective: str | None
    window_index: int | None
    rank: int | None
    status: str
    created_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "OptimizationTrialDTO":
        return OptimizationTrialDTO(
            id=entity.id,
            optimization_run_id=entity.optimization_run_id,
            backtest_run_id=entity.backtest_run_id,
            parameters=entity.parameters,
            objective_value=str(entity.objective_value)
            if entity.objective_value is not None
            else None,
            in_sample_objective=str(entity.in_sample_objective)
            if entity.in_sample_objective is not None
            else None,
            window_index=entity.window_index,
            rank=entity.rank,
            status=entity.status.value,
            created_at=entity.created_at,
        )
