from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.strategy.domain.value_objects import (
    IndicatorDefinition,
    Strategy,
    StrategyVersion,
)
from alphaedge.modules.strategy.domain.deployment import StrategyDeployment


class StrategyRepository(ABC):
    @abstractmethod
    async def save(self, strategy: Strategy) -> Strategy:
        pass

    @abstractmethod
    async def get_by_id(self, strategy_id: UUID) -> Strategy | None:
        pass

    @abstractmethod
    async def get_by_user_and_name(self, user_id: UUID, name: str) -> Strategy | None:
        pass

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, active_only: bool = True, limit: int = 50, offset: int = 0
    ) -> list[Strategy]:
        pass

    @abstractmethod
    async def count_by_user(self, user_id: UUID, *, active_only: bool = True) -> int:
        pass

    @abstractmethod
    async def soft_delete(self, strategy: Strategy) -> None:
        pass


class StrategyVersionRepository(ABC):
    @abstractmethod
    async def save(self, version: StrategyVersion) -> StrategyVersion:
        pass

    @abstractmethod
    async def get_by_id(self, version_id: UUID) -> StrategyVersion | None:
        pass

    @abstractmethod
    async def get_by_strategy_and_version(
        self, strategy_id: UUID, version: int
    ) -> StrategyVersion | None:
        pass

    @abstractmethod
    async def list_by_strategy(self, strategy_id: UUID) -> list[StrategyVersion]:
        pass

    @abstractmethod
    async def next_version_number(self, strategy_id: UUID) -> int:
        pass


class IndicatorRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[IndicatorDefinition]:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> IndicatorDefinition | None:
        pass


class StrategyDeploymentRepository(ABC):
    @abstractmethod
    async def save(self, deployment: StrategyDeployment) -> StrategyDeployment:
        pass

    @abstractmethod
    async def get_by_id(self, deployment_id: UUID) -> StrategyDeployment | None:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[StrategyDeployment]:
        pass

    @abstractmethod
    async def list_active_for_instrument(self, instrument_id: UUID) -> list[StrategyDeployment]:
        pass
