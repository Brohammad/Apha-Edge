from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.optimization.domain.entities import OptimizationRun, OptimizationTrial


class OptimizationRunRepository(ABC):
    @abstractmethod
    async def save(self, run: OptimizationRun) -> OptimizationRun:
        pass

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> OptimizationRun | None:
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[OptimizationRun]:
        pass

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        pass

    @abstractmethod
    async def update(self, run: OptimizationRun) -> OptimizationRun:
        pass


class OptimizationTrialRepository(ABC):
    @abstractmethod
    async def save(self, trial: OptimizationTrial) -> OptimizationTrial:
        pass

    @abstractmethod
    async def save_many(self, trials: list[OptimizationTrial]) -> list[OptimizationTrial]:
        pass

    @abstractmethod
    async def get_by_id(self, trial_id: UUID) -> OptimizationTrial | None:
        pass

    @abstractmethod
    async def list_by_run_id(self, run_id: UUID) -> list[OptimizationTrial]:
        pass

    @abstractmethod
    async def update(self, trial: OptimizationTrial) -> OptimizationTrial:
        pass

    @abstractmethod
    async def update_many(self, trials: list[OptimizationTrial]) -> None:
        pass
