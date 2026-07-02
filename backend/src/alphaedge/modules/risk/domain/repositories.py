from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.risk.domain.entities import RiskLimit, RiskSnapshot


class RiskSnapshotRepository(ABC):
    @abstractmethod
    async def save(self, snapshot: RiskSnapshot) -> RiskSnapshot:
        pass

    @abstractmethod
    async def get_by_id(self, snapshot_id: UUID) -> RiskSnapshot | None:
        pass

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> list[RiskSnapshot]:
        pass

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> RiskSnapshot | None:
        pass


class RiskLimitRepository(ABC):
    @abstractmethod
    async def save(self, limit: RiskLimit) -> RiskLimit:
        pass

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RiskLimit]:
        pass

    @abstractmethod
    async def upsert(self, limit: RiskLimit) -> RiskLimit:
        pass

    @abstractmethod
    async def get_by_portfolio_and_type(
        self, portfolio_id: UUID, limit_type: str
    ) -> RiskLimit | None:
        pass
