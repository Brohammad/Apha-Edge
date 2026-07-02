from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from alphaedge.modules.insights.domain.enums import InsightStatus, InsightType, SourceType
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class InsightRequest:
    id: UUID
    user_id: UUID
    insight_type: InsightType
    source_type: SourceType
    source_id: UUID
    status: InsightStatus
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        insight_type: InsightType,
        source_type: SourceType,
        source_id: UUID,
    ) -> "InsightRequest":
        return InsightRequest(
            id=uuid4(),
            user_id=user_id,
            insight_type=insight_type,
            source_type=source_type,
            source_id=source_id,
            status=InsightStatus.QUEUED,
        )

    def mark_running(self) -> None:
        self.status = InsightStatus.RUNNING
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        self.status = InsightStatus.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_failed(self, reason: str) -> None:
        self.status = InsightStatus.FAILED
        self.error_message = reason[:2000]
        self.updated_at = datetime.now(UTC)


@dataclass
class InsightReport:
    id: UUID
    insight_request_id: UUID
    content: str
    metadata: dict[str, object]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        insight_request_id: UUID,
        content: str,
        metadata: dict[str, object],
    ) -> "InsightReport":
        content = content.strip()
        if not content:
            raise ValidationError("Insight report content cannot be empty")
        return InsightReport(
            id=uuid4(),
            insight_request_id=insight_request_id,
            content=content,
            metadata=metadata,
        )
