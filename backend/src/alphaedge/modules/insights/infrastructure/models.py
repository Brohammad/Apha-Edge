from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.insights.domain.entities import InsightReport, InsightRequest
from alphaedge.modules.insights.domain.enums import InsightStatus, InsightType, SourceType
from alphaedge.modules.insights.domain.repositories import (
    InsightReportRepository,
    InsightRequestRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InsightRequestModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "insight_requests"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    insight_type: Mapped[str] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(nullable=False)
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(default=InsightStatus.QUEUED.value, index=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(nullable=True)


class InsightReportModel(Base):
    __tablename__ = "insight_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    insight_request_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), unique=True, nullable=False
    )
    content: Mapped[str] = mapped_column(nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


def _request_to_entity(m: InsightRequestModel) -> InsightRequest:
    return InsightRequest(
        id=m.id,
        user_id=m.user_id,
        insight_type=InsightType(m.insight_type),
        source_type=SourceType(m.source_type),
        source_id=m.source_id,
        status=InsightStatus(m.status),
        error_message=m.error_message,
        celery_task_id=m.celery_task_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _report_to_entity(m: InsightReportModel) -> InsightReport:
    return InsightReport(
        id=m.id,
        insight_request_id=m.insight_request_id,
        content=m.content,
        metadata=m.metadata_,
        created_at=m.created_at,
    )


class SQLAlchemyInsightRequestRepository(InsightRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, request: InsightRequest) -> InsightRequest:
        model = InsightRequestModel(
            id=request.id,
            user_id=request.user_id,
            insight_type=request.insight_type.value,
            source_type=request.source_type.value,
            source_id=request.source_id,
            status=request.status.value,
            error_message=request.error_message,
            celery_task_id=request.celery_task_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _request_to_entity(model)

    async def get_by_id(self, request_id: UUID) -> InsightRequest | None:
        model = await self._session.get(InsightRequestModel, request_id)
        return _request_to_entity(model) if model else None

    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[InsightRequest]:
        stmt = (
            select(InsightRequestModel)
            .where(InsightRequestModel.user_id == user_id)
            .order_by(InsightRequestModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_request_to_entity(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(InsightRequestModel)
            .where(InsightRequestModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update(self, request: InsightRequest) -> InsightRequest:
        model = await self._session.get(InsightRequestModel, request.id)
        if not model:
            raise ValueError(f"InsightRequest {request.id} not found")
        model.status = request.status.value
        model.error_message = request.error_message
        model.celery_task_id = request.celery_task_id
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _request_to_entity(model)


class SQLAlchemyInsightReportRepository(InsightReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: InsightReport) -> InsightReport:
        model = InsightReportModel(
            id=report.id,
            insight_request_id=report.insight_request_id,
            content=report.content,
            metadata_=report.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return _report_to_entity(model)

    async def get_by_request_id(self, request_id: UUID) -> InsightReport | None:
        stmt = select(InsightReportModel).where(
            InsightReportModel.insight_request_id == request_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _report_to_entity(model) if model else None
