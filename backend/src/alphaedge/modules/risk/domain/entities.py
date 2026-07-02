from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.portfolio.domain.enums import RiskLimitType
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class RiskSnapshot:
    id: UUID
    portfolio_id: UUID
    snapshot_at: datetime
    var_95: Decimal | None
    var_99: Decimal | None
    max_drawdown: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    beta: Decimal | None
    alpha: Decimal | None
    volatility: Decimal | None
    correlation_matrix: dict[str, object] | None
    metrics: dict[str, object]

    @staticmethod
    def create(
        portfolio_id: UUID,
        *,
        var_95: Decimal | None = None,
        var_99: Decimal | None = None,
        max_drawdown: Decimal | None = None,
        sharpe_ratio: Decimal | None = None,
        sortino_ratio: Decimal | None = None,
        beta: Decimal | None = None,
        alpha: Decimal | None = None,
        volatility: Decimal | None = None,
        correlation_matrix: dict[str, object] | None = None,
        metrics: dict[str, object] | None = None,
    ) -> "RiskSnapshot":
        return RiskSnapshot(
            id=uuid4(),
            portfolio_id=portfolio_id,
            snapshot_at=datetime.now(UTC),
            var_95=var_95,
            var_99=var_99,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            beta=beta,
            alpha=alpha,
            volatility=volatility,
            correlation_matrix=correlation_matrix,
            metrics=metrics or {},
        )


@dataclass
class RiskLimit:
    id: UUID
    portfolio_id: UUID
    limit_type: RiskLimitType
    threshold: Decimal
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        portfolio_id: UUID,
        limit_type: RiskLimitType,
        threshold: Decimal,
        *,
        is_active: bool = True,
    ) -> "RiskLimit":
        if threshold <= 0:
            raise ValidationError("Risk limit threshold must be positive")
        return RiskLimit(
            id=uuid4(),
            portfolio_id=portfolio_id,
            limit_type=limit_type,
            threshold=threshold,
            is_active=is_active,
        )
