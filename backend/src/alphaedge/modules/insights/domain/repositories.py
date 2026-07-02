from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.insights.domain.entities import InsightReport, InsightRequest


class InsightRequestRepository(ABC):
    @abstractmethod
    async def save(self, request: InsightRequest) -> InsightRequest:
        pass

    @abstractmethod
    async def get_by_id(self, request_id: UUID) -> InsightRequest | None:
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[InsightRequest]:
        pass

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        pass

    @abstractmethod
    async def update(self, request: InsightRequest) -> InsightRequest:
        pass


class InsightReportRepository(ABC):
    @abstractmethod
    async def save(self, report: InsightReport) -> InsightReport:
        pass

    @abstractmethod
    async def get_by_request_id(self, request_id: UUID) -> InsightReport | None:
        pass
