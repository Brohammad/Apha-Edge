from uuid import UUID

from alphaedge.modules.insights.application.commands import (
    GetInsightQuery,
    InsightReportDTO,
    InsightRequestDTO,
    ListInsightsQuery,
    PerformanceReportCommand,
    RequestInsightCommand,
    StrategyExplainCommand,
)
from alphaedge.modules.insights.domain.entities import InsightRequest
from alphaedge.modules.insights.domain.enums import InsightType, SourceType
from alphaedge.modules.insights.domain.repositories import (
    InsightReportRepository,
    InsightRequestRepository,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


class RequestInsightHandler:
    def __init__(self, request_repo: InsightRequestRepository) -> None:
        self._request_repo = request_repo

    async def handle(self, command: RequestInsightCommand) -> InsightRequestDTO:
        try:
            insight_type = InsightType(command.insight_type)
        except ValueError as exc:
            raise ValidationError(f"Invalid insight type: {command.insight_type}") from exc
        try:
            source_type = SourceType(command.source_type)
        except ValueError as exc:
            raise ValidationError(f"Invalid source type: {command.source_type}") from exc

        request = InsightRequest.create(
            user_id=command.user_id,
            insight_type=insight_type,
            source_type=source_type,
            source_id=command.source_id,
        )
        saved = await self._request_repo.save(request)
        return InsightRequestDTO.from_entity(saved)


class StrategyExplainHandler:
    def __init__(self, request_repo: InsightRequestRepository) -> None:
        self._request_repo = request_repo

    async def handle(self, command: StrategyExplainCommand) -> InsightRequestDTO:
        if command.strategy_version_id:
            source_type = SourceType.STRATEGY_VERSION
            source_id = command.strategy_version_id
        elif command.strategy_id:
            source_type = SourceType.STRATEGY
            source_id = command.strategy_id
        else:
            raise ValidationError("strategy_id or strategy_version_id is required")

        return await RequestInsightHandler(self._request_repo).handle(
            RequestInsightCommand(
                user_id=command.user_id,
                insight_type=InsightType.STRATEGY_EXPLANATION.value,
                source_type=source_type.value,
                source_id=source_id,
            )
        )


class PerformanceReportHandler:
    def __init__(self, request_repo: InsightRequestRepository) -> None:
        self._request_repo = request_repo

    async def handle(self, command: PerformanceReportCommand) -> InsightRequestDTO:
        return await RequestInsightHandler(self._request_repo).handle(
            RequestInsightCommand(
                user_id=command.user_id,
                insight_type=InsightType.PERFORMANCE_REPORT.value,
                source_type=SourceType.BACKTEST.value,
                source_id=command.backtest_run_id,
            )
        )


class ListInsightsHandler:
    def __init__(self, request_repo: InsightRequestRepository) -> None:
        self._request_repo = request_repo

    async def handle(self, query: ListInsightsQuery) -> tuple[list[InsightRequestDTO], int]:
        items = await self._request_repo.list_by_user(
            query.user_id, limit=query.limit, offset=query.offset
        )
        total = await self._request_repo.count_by_user(query.user_id)
        return [InsightRequestDTO.from_entity(r) for r in items], total


class GetInsightHandler:
    def __init__(
        self,
        request_repo: InsightRequestRepository,
        report_repo: InsightReportRepository,
    ) -> None:
        self._request_repo = request_repo
        self._report_repo = report_repo

    async def handle(
        self, query: GetInsightQuery
    ) -> tuple[InsightRequestDTO, InsightReportDTO | None]:
        request = await _get_owned_request(self._request_repo, query.user_id, query.request_id)
        report = await self._report_repo.get_by_request_id(request.id)
        report_dto = InsightReportDTO.from_entity(report) if report else None
        return InsightRequestDTO.from_entity(request), report_dto


async def _get_owned_request(
    repo: InsightRequestRepository, user_id: UUID, request_id: UUID
) -> InsightRequest:
    request = await repo.get_by_id(request_id)
    if not request:
        raise NotFoundError("InsightRequest", str(request_id))
    if request.user_id != user_id:
        raise AuthorizationError("You do not own this insight request")
    return request
