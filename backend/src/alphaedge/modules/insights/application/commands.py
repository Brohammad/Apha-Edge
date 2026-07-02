from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class RequestInsightCommand:
    user_id: UUID
    insight_type: str
    source_type: str
    source_id: UUID


@dataclass(frozen=True)
class StrategyExplainCommand:
    user_id: UUID
    strategy_version_id: UUID | None = None
    strategy_id: UUID | None = None


@dataclass(frozen=True)
class PerformanceReportCommand:
    user_id: UUID
    backtest_run_id: UUID


@dataclass(frozen=True)
class ListInsightsQuery:
    user_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetInsightQuery:
    user_id: UUID
    request_id: UUID


@dataclass(frozen=True)
class InsightRequestDTO:
    id: UUID
    user_id: UUID
    insight_type: str
    source_type: str
    source_id: UUID
    status: str
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "InsightRequestDTO":
        return InsightRequestDTO(
            id=entity.id,
            user_id=entity.user_id,
            insight_type=entity.insight_type.value,
            source_type=entity.source_type.value,
            source_id=entity.source_id,
            status=entity.status.value,
            error_message=entity.error_message,
            celery_task_id=entity.celery_task_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class InsightReportDTO:
    id: UUID
    insight_request_id: UUID
    content: str
    metadata: dict[str, object]
    created_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "InsightReportDTO":
        return InsightReportDTO(
            id=entity.id,
            insight_request_id=entity.insight_request_id,
            content=entity.content,
            metadata=entity.metadata,
            created_at=entity.created_at,
        )
