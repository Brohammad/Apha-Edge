from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.config import settings
from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.insights.application.commands import (
    GetInsightQuery,
    ListInsightsQuery,
    PerformanceReportCommand,
    RequestInsightCommand,
    StrategyExplainCommand,
)
from alphaedge.modules.insights.application.handlers import (
    GetInsightHandler,
    ListInsightsHandler,
    PerformanceReportHandler,
    RequestInsightHandler,
    StrategyExplainHandler,
)
from alphaedge.modules.insights.infrastructure.models import (
    SQLAlchemyInsightReportRepository,
    SQLAlchemyInsightRequestRepository,
)
from alphaedge.modules.insights.infrastructure.runner import execute_insight
from alphaedge.modules.insights.infrastructure.tasks import generate_insight_task
from alphaedge.modules.insights.presentation.schemas import (
    InsightDetailResponse,
    InsightReportResponse,
    InsightRequestResponse,
    PerformanceReportRequest,
    RequestInsightRequest,
    StrategyExplainRequest,
)
from alphaedge.shared.presentation.envelope import success_response

insights_router = APIRouter(prefix="/insights", tags=["AI Insights"])


def _repos(session: AsyncSession):
    return (
        SQLAlchemyInsightRequestRepository(session),
        SQLAlchemyInsightReportRepository(session),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_request(dto: object) -> dict:
    return InsightRequestResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        insight_type=dto.insight_type,
        source_type=dto.source_type,
        source_id=str(dto.source_id),
        status=dto.status,
        error_message=dto.error_message,
        celery_task_id=dto.celery_task_id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_report(dto: object) -> dict:
    return InsightReportResponse(
        id=str(dto.id),
        insight_request_id=str(dto.insight_request_id),
        content=dto.content,
        metadata=dto.metadata,
        created_at=dto.created_at,
    ).model_dump(mode="json")


async def _enqueue(session: AsyncSession, result: object) -> object:
    request_repo, _ = _repos(session)
    await session.commit()
    # In development, run in-process so insight code matches the live API (no stale Celery worker).
    if settings.app_env == "development":
        await execute_insight(result.id)
        return result
    task = generate_insight_task.delay(str(result.id))
    entity = await request_repo.get_by_id(result.id)
    if entity:
        entity.celery_task_id = task.id
        await request_repo.update(entity)
    return result


@insights_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def request_insight(
    body: RequestInsightRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    request_repo, _ = _repos(session)
    handler = RequestInsightHandler(request_repo)
    result = await handler.handle(
        RequestInsightCommand(
            user_id=user_id,
            insight_type=body.insight_type,
            source_type=body.source_type,
            source_id=UUID(body.source_id),
        )
    )
    result = await _enqueue(session, result)
    return success_response(_to_request(result), request_id=_request_id(request))


@insights_router.post("/strategy-explain", status_code=status.HTTP_202_ACCEPTED)
async def strategy_explain(
    body: StrategyExplainRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    request_repo, _ = _repos(session)
    handler = StrategyExplainHandler(request_repo)
    result = await handler.handle(
        StrategyExplainCommand(
            user_id=user_id,
            strategy_id=UUID(body.strategy_id) if body.strategy_id else None,
            strategy_version_id=UUID(body.strategy_version_id)
            if body.strategy_version_id
            else None,
        )
    )
    result = await _enqueue(session, result)
    return success_response(_to_request(result), request_id=_request_id(request))


@insights_router.post("/performance-report", status_code=status.HTTP_202_ACCEPTED)
async def performance_report(
    body: PerformanceReportRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    request_repo, _ = _repos(session)
    handler = PerformanceReportHandler(request_repo)
    result = await handler.handle(
        PerformanceReportCommand(
            user_id=user_id,
            backtest_run_id=UUID(body.backtest_run_id),
        )
    )
    result = await _enqueue(session, result)
    return success_response(_to_request(result), request_id=_request_id(request))


@insights_router.get("")
async def list_insights(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    request_repo, _ = _repos(session)
    handler = ListInsightsHandler(request_repo)
    items, total = await handler.handle(
        ListInsightsQuery(user_id=user_id, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_request(r) for r in items], "total_count": total},
        request_id=_request_id(request),
    )


@insights_router.get("/{insight_id}")
async def get_insight(
    insight_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    request_repo, report_repo = _repos(session)
    handler = GetInsightHandler(request_repo, report_repo)
    req_dto, report_dto = await handler.handle(
        GetInsightQuery(user_id=user_id, request_id=insight_id)
    )
    payload = InsightDetailResponse(
        request=InsightRequestResponse(
            id=str(req_dto.id),
            user_id=str(req_dto.user_id),
            insight_type=req_dto.insight_type,
            source_type=req_dto.source_type,
            source_id=str(req_dto.source_id),
            status=req_dto.status,
            error_message=req_dto.error_message,
            celery_task_id=req_dto.celery_task_id,
            created_at=req_dto.created_at,
            updated_at=req_dto.updated_at,
        ),
        report=InsightReportResponse(
            id=str(report_dto.id),
            insight_request_id=str(report_dto.insight_request_id),
            content=report_dto.content,
            metadata=report_dto.metadata,
            created_at=report_dto.created_at,
        )
        if report_dto
        else None,
    )
    return success_response(payload.model_dump(mode="json"), request_id=_request_id(request))
