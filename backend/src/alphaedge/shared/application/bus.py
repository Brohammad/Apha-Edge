from abc import ABC, abstractmethod
from typing import Any


class CommandHandler[TCommand, TResult](ABC):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult: ...


class QueryHandler[TQuery, TResult](ABC):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult: ...


class EventBus(ABC):
    @abstractmethod
    async def publish(self, event: Any) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type, handler: Any) -> None: ...


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type, list[Any]] = {}

    async def publish(self, event: Any) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            await handler(event)

    def subscribe(self, event_type: type, handler: Any) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
