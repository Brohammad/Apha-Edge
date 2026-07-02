from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.strategy.domain.enums import SignalAction, StrategyType, VersionStatus
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Signal:
    action: SignalAction
    reason: str = ""


@dataclass
class Tick:
    timestamp: datetime
    price: Decimal
    size: Decimal


@dataclass
class StrategyContext:
    """Runtime context passed to strategy lifecycle hooks."""

    parameters: dict[str, object] = field(default_factory=dict)
    indicators: dict[str, object] = field(default_factory=dict)
    position: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")


@dataclass
class Strategy:
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    strategy_type: StrategyType
    is_active: bool = True
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        name: str,
        strategy_type: StrategyType,
        description: str | None = None,
    ) -> "Strategy":
        name = name.strip()
        if not name:
            raise ValidationError("Strategy name is required")
        if len(name) > 255:
            raise ValidationError("Strategy name must be at most 255 characters")
        return Strategy(
            id=uuid4(),
            user_id=user_id,
            name=name,
            description=description.strip() if description else None,
            strategy_type=strategy_type,
        )


@dataclass
class StrategyVersion:
    id: UUID
    strategy_id: UUID
    version: int
    source_code: str
    parameters: dict[str, object]
    compiled_hash: str | None
    status: VersionStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        strategy_id: UUID,
        version: int,
        source_code: str,
        parameters: dict[str, object] | None = None,
    ) -> "StrategyVersion":
        source_code = source_code.strip()
        if not source_code:
            raise ValidationError("Source code is required")
        return StrategyVersion(
            id=uuid4(),
            strategy_id=strategy_id,
            version=version,
            source_code=source_code,
            parameters=parameters or {},
            compiled_hash=None,
            status=VersionStatus.DRAFT,
        )

    def mark_validated(self, compiled_hash: str) -> None:
        self.compiled_hash = compiled_hash
        self.status = VersionStatus.VALIDATED


@dataclass(frozen=True)
class IndicatorDefinition:
    id: UUID
    name: str
    category: str
    parameters_schema: dict[str, object]
    implementation: str
