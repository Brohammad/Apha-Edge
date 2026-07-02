from datetime import datetime

from pydantic import BaseModel, Field


class RiskLimitItem(BaseModel):
    limit_type: str
    threshold: str
    is_active: bool = True


class UpdateRiskLimitsRequest(BaseModel):
    limits: list[RiskLimitItem] = Field(min_length=1)


class RiskSnapshotResponse(BaseModel):
    id: str
    portfolio_id: str
    snapshot_at: datetime
    var_95: str | None
    var_99: str | None
    max_drawdown: str | None
    sharpe_ratio: str | None
    sortino_ratio: str | None
    beta: str | None
    alpha: str | None
    volatility: str | None
    correlation_matrix: dict[str, object] | None
    metrics: dict[str, object]
    violations: list[dict[str, object]]


class RiskLimitResponse(BaseModel):
    id: str
    portfolio_id: str
    limit_type: str
    threshold: str
    is_active: bool
