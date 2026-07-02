from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.backtesting.domain.entities import (
    BacktestResult,
    BacktestRun,
    BacktestTrade,
)


class BacktestRunRepository(ABC):
    @abstractmethod
    async def save(self, run: BacktestRun) -> BacktestRun:
        pass

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> BacktestRun | None:
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[BacktestRun]:
        pass

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        pass

    @abstractmethod
    async def update(self, run: BacktestRun) -> BacktestRun:
        pass


class BacktestResultRepository(ABC):
    @abstractmethod
    async def save(self, result: BacktestResult) -> BacktestResult:
        pass

    @abstractmethod
    async def get_by_run_id(self, run_id: UUID) -> BacktestResult | None:
        pass


class BacktestTradeRepository(ABC):
    @abstractmethod
    async def save_many(self, trades: list[BacktestTrade]) -> None:
        pass

    @abstractmethod
    async def list_by_run_id(self, run_id: UUID) -> list[BacktestTrade]:
        pass
