"""Strategy loss analysis workflow."""

from uuid import UUID

from alphaedge.modules.insights.application.commands import PerformanceReportCommand
from alphaedge.modules.insights.domain.enums import InsightType
from alphaedge.modules.insights.domain.repositories import InsightRequestRepository


class StrategyLossAnalysisHandler:
    def __init__(self, request_repo: InsightRequestRepository) -> None:
        self._request_repo = request_repo

    async def handle(self, command: PerformanceReportCommand):
        from alphaedge.modules.insights.application.handlers import PerformanceReportHandler

        handler = PerformanceReportHandler(self._request_repo)
        result = await handler.handle(command)
        entity = await self._request_repo.get_by_id(result.id)
        if entity:
            entity.insight_type = InsightType.STRATEGY_LOSS_ANALYSIS
            await self._request_repo.update(entity)
        return result
