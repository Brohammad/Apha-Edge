from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from alphaedge.modules.execution.domain.entities import Order


@dataclass(frozen=True)
class FillResponse:
    filled_quantity: Decimal
    fill_price: Decimal
    commission: Decimal


@dataclass(frozen=True)
class OrderAck:
    broker_order_id: str
    fill: FillResponse | None = None


@dataclass(frozen=True)
class CancelAck:
    cancelled: bool
    message: str = ""


class BrokerPort(ABC):
    @abstractmethod
    async def submit_order(self, order: Order, market_price: Decimal) -> OrderAck:
        pass

    @abstractmethod
    async def cancel_order(self, order: Order) -> CancelAck:
        pass
