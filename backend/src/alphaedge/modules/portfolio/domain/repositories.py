from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio, RebalancePlan


class PortfolioRepository(ABC):
    @abstractmethod
    async def save(self, portfolio: Portfolio) -> Portfolio:
        pass

    @abstractmethod
    async def get_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Portfolio]:
        pass

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        pass

    @abstractmethod
    async def update(self, portfolio: Portfolio) -> Portfolio:
        pass


class HoldingRepository(ABC):
    @abstractmethod
    async def save(self, holding: Holding) -> Holding:
        pass

    @abstractmethod
    async def get_by_portfolio_and_instrument(
        self, portfolio_id: UUID, instrument_id: UUID
    ) -> Holding | None:
        pass

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[Holding]:
        pass

    @abstractmethod
    async def upsert(self, holding: Holding) -> Holding:
        pass

    @abstractmethod
    async def delete(self, holding_id: UUID) -> None:
        pass


class RebalancePlanRepository(ABC):
    @abstractmethod
    async def save(self, plan: RebalancePlan) -> RebalancePlan:
        pass

    @abstractmethod
    async def get_by_id(self, plan_id: UUID) -> RebalancePlan | None:
        pass

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> list[RebalancePlan]:
        pass
