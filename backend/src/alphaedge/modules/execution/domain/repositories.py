from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.execution.domain.entities import (
    BrokerConnection,
    Execution,
    Order,
    OrderEvent,
)


class BrokerConnectionRepository(ABC):
    @abstractmethod
    async def save(self, connection: BrokerConnection) -> BrokerConnection:
        pass

    @abstractmethod
    async def get_by_id(self, connection_id: UUID) -> BrokerConnection | None:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[BrokerConnection]:
        pass

    @abstractmethod
    async def update(self, connection: BrokerConnection) -> BrokerConnection:
        pass


class OrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> Order:
        pass

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> Order | None:
        pass

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> Order | None:
        pass

    @abstractmethod
    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        pass

    @abstractmethod
    async def count_by_portfolio(self, portfolio_id: UUID) -> int:
        pass

    @abstractmethod
    async def update(self, order: Order) -> Order:
        pass


class ExecutionRepository(ABC):
    @abstractmethod
    async def save(self, execution: Execution) -> Execution:
        pass

    @abstractmethod
    async def list_by_order_id(self, order_id: UUID) -> list[Execution]:
        pass


class OrderEventRepository(ABC):
    @abstractmethod
    async def save(self, event: OrderEvent) -> OrderEvent:
        pass

    @abstractmethod
    async def list_by_order_id(self, order_id: UUID) -> list[OrderEvent]:
        pass
