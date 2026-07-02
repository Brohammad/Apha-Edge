from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.risk.domain.entities import RiskLimit, RiskSnapshot


@dataclass(frozen=True)
class ComputeRiskCommand:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class ListRiskSnapshotsQuery:
    user_id: UUID
    portfolio_id: UUID
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class GetLatestRiskSnapshotQuery:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class GetRiskLimitsQuery:
    user_id: UUID
    portfolio_id: UUID


@dataclass(frozen=True)
class UpdateRiskLimitsCommand:
    user_id: UUID
    portfolio_id: UUID
    limits: list[dict[str, object]]


@dataclass(frozen=True)
class RiskSnapshotDTO:
    id: UUID
    portfolio_id: UUID
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

    @staticmethod
    def from_entity(
        entity: RiskSnapshot, violations: list[dict[str, object]] | None = None
    ) -> "RiskSnapshotDTO":
        def _s(v: Decimal | None) -> str | None:
            return str(v) if v is not None else None

        return RiskSnapshotDTO(
            id=entity.id,
            portfolio_id=entity.portfolio_id,
            snapshot_at=entity.snapshot_at,
            var_95=_s(entity.var_95),
            var_99=_s(entity.var_99),
            max_drawdown=_s(entity.max_drawdown),
            sharpe_ratio=_s(entity.sharpe_ratio),
            sortino_ratio=_s(entity.sortino_ratio),
            beta=_s(entity.beta),
            alpha=_s(entity.alpha),
            volatility=_s(entity.volatility),
            correlation_matrix=entity.correlation_matrix,
            metrics=entity.metrics,
            violations=violations or [],
        )


@dataclass(frozen=True)
class RiskLimitDTO:
    id: UUID
    portfolio_id: UUID
    limit_type: str
    threshold: str
    is_active: bool

    @staticmethod
    def from_entity(entity: RiskLimit) -> "RiskLimitDTO":
        return RiskLimitDTO(
            id=entity.id,
            portfolio_id=entity.portfolio_id,
            limit_type=entity.limit_type.value,
            threshold=str(entity.threshold),
            is_active=entity.is_active,
        )
