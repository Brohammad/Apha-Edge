from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alphaedge.modules.strategy.domain.enums import StrategyType
from alphaedge.modules.strategy.domain.value_objects import (
    IndicatorDefinition,
    Strategy,
    StrategyVersion,
)


@dataclass(frozen=True)
class CreateStrategyCommand:
    user_id: UUID
    name: str
    strategy_type: StrategyType
    description: str | None = None
    source_code: str | None = None
    parameters: dict[str, object] | None = None


@dataclass(frozen=True)
class UpdateStrategyCommand:
    user_id: UUID
    strategy_id: UUID
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class DeleteStrategyCommand:
    user_id: UUID
    strategy_id: UUID


@dataclass(frozen=True)
class CreateStrategyVersionCommand:
    user_id: UUID
    strategy_id: UUID
    source_code: str
    parameters: dict[str, object] | None = None


@dataclass(frozen=True)
class ValidateStrategyVersionCommand:
    user_id: UUID
    strategy_id: UUID
    version_id: UUID


@dataclass(frozen=True)
class ListStrategiesQuery:
    user_id: UUID
    active_only: bool = True
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetStrategyQuery:
    user_id: UUID
    strategy_id: UUID


@dataclass(frozen=True)
class ListStrategyVersionsQuery:
    user_id: UUID
    strategy_id: UUID


@dataclass(frozen=True)
class GetStrategyVersionQuery:
    user_id: UUID
    strategy_id: UUID
    version_id: UUID


@dataclass(frozen=True)
class ListIndicatorsQuery:
    pass


@dataclass(frozen=True)
class StrategyDTO:
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    strategy_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: Strategy) -> "StrategyDTO":
        return StrategyDTO(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name,
            description=entity.description,
            strategy_type=entity.strategy_type.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class StrategyVersionDTO:
    id: UUID
    strategy_id: UUID
    version: int
    source_code: str
    parameters: dict[str, object]
    compiled_hash: str | None
    status: str
    created_at: datetime

    @staticmethod
    def from_entity(entity: StrategyVersion) -> "StrategyVersionDTO":
        return StrategyVersionDTO(
            id=entity.id,
            strategy_id=entity.strategy_id,
            version=entity.version,
            source_code=entity.source_code,
            parameters=entity.parameters,
            compiled_hash=entity.compiled_hash,
            status=entity.status.value,
            created_at=entity.created_at,
        )


@dataclass(frozen=True)
class IndicatorDTO:
    id: UUID
    name: str
    category: str
    parameters_schema: dict[str, object]
    implementation: str

    @staticmethod
    def from_entity(entity: IndicatorDefinition) -> "IndicatorDTO":
        return IndicatorDTO(
            id=entity.id,
            name=entity.name,
            category=entity.category,
            parameters_schema=entity.parameters_schema,
            implementation=entity.implementation,
        )


@dataclass(frozen=True)
class ValidationResultDTO:
    version_id: UUID
    status: str
    compiled_hash: str
    errors: list[str]
