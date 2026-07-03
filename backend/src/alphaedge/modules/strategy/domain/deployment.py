"""Strategy deployment domain entity for live/paper signal evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.strategy.domain.enums import VersionStatus
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class StrategyDeployment:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_ids: list[UUID]
    quantity: Decimal
    is_active: bool = True
    last_signal_at: datetime | None = None
    last_signal_action: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        strategy_version_id: UUID,
        portfolio_id: UUID,
        broker_connection_id: UUID,
        instrument_ids: list[UUID],
        quantity: Decimal,
    ) -> StrategyDeployment:
        if not instrument_ids:
            raise ValidationError("At least one instrument is required")
        if quantity <= 0:
            raise ValidationError("Deployment quantity must be positive")
        return StrategyDeployment(
            id=uuid4(),
            user_id=user_id,
            strategy_version_id=strategy_version_id,
            portfolio_id=portfolio_id,
            broker_connection_id=broker_connection_id,
            instrument_ids=list(instrument_ids),
            quantity=quantity,
        )

    def pause(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def resume(self) -> None:
        self.is_active = True
        self.updated_at = datetime.now(UTC)

    def record_signal(self, action: str, at: datetime | None = None) -> None:
        self.last_signal_action = action
        self.last_signal_at = at or datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


def require_validated_version(status: VersionStatus) -> None:
    if status != VersionStatus.VALIDATED:
        raise ValidationError("Strategy version must be validated before deployment")
