from datetime import datetime

from pydantic import BaseModel, Field


class SubmitOptimizationRequest(BaseModel):
    strategy_version_id: str
    name: str = Field(min_length=1, max_length=255)
    method: str = Field(default="grid_search")
    objective: str = Field(default="sharpe_ratio")
    parameter_space: dict[str, list[object]]
    backtest_config: dict[str, object]
    walk_forward_config: dict[str, object] | None = None


class OptimizationRunResponse(BaseModel):
    id: str
    user_id: str
    strategy_version_id: str
    name: str
    method: str
    objective: str
    parameter_space: dict[str, object]
    backtest_config: dict[str, object]
    walk_forward_config: dict[str, object] | None
    status: str
    best_trial_id: str | None
    total_trials: int
    completed_trials: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime


class OptimizationTrialResponse(BaseModel):
    id: str
    optimization_run_id: str
    backtest_run_id: str | None
    parameters: dict[str, object]
    objective_value: str | None
    in_sample_objective: str | None
    window_index: int | None
    rank: int | None
    status: str
    created_at: datetime
