from enum import StrEnum


class OptimizationMethod(StrEnum):
    GRID_SEARCH = "grid_search"
    WALK_FORWARD = "walk_forward"


class OptimizationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationObjective(StrEnum):
    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"


class TrialStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
