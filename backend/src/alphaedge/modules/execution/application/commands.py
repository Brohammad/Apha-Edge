from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateBrokerConnectionCommand:
    user_id: UUID
    broker_name: str
    credentials: dict[str, object] | None = None
    is_paper: bool = True


@dataclass(frozen=True)
class DeleteBrokerConnectionCommand:
    user_id: UUID
    connection_id: UUID


@dataclass(frozen=True)
class ListBrokerConnectionsQuery:
    user_id: UUID


@dataclass(frozen=True)
class SubmitOrderCommand:
    user_id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    side: str
    order_type: str
    quantity: str
    limit_price: str | None = None
    stop_price: str | None = None
    idempotency_key: str | None = None
    live_trading_acknowledged: bool = False
    product_type: str = "CNC"
    exchange_segment: str | None = None


@dataclass(frozen=True)
class ListOrdersQuery:
    user_id: UUID
    portfolio_id: UUID | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetOrderQuery:
    user_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class CancelOrderCommand:
    user_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class ListExecutionsQuery:
    user_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class BrokerConnectionDTO:
    id: UUID
    user_id: UUID
    broker_name: str
    is_paper: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "BrokerConnectionDTO":
        return BrokerConnectionDTO(
            id=entity.id,
            user_id=entity.user_id,
            broker_name=entity.broker_name.value,
            is_paper=entity.is_paper,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class OrderDTO:
    id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    side: str
    order_type: str
    quantity: str
    filled_quantity: str
    limit_price: str | None
    stop_price: str | None
    status: str
    broker_order_id: str | None
    idempotency_key: str | None
    product_type: str
    exchange_segment: str | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "OrderDTO":
        return OrderDTO(
            id=entity.id,
            portfolio_id=entity.portfolio_id,
            broker_connection_id=entity.broker_connection_id,
            instrument_id=entity.instrument_id,
            side=entity.side.value,
            order_type=entity.order_type.value,
            quantity=str(entity.quantity),
            filled_quantity=str(entity.filled_quantity),
            limit_price=str(entity.limit_price) if entity.limit_price is not None else None,
            stop_price=str(entity.stop_price) if entity.stop_price is not None else None,
            status=entity.status.value,
            broker_order_id=entity.broker_order_id,
            idempotency_key=entity.idempotency_key,
            product_type=entity.product_type.value,
            exchange_segment=entity.exchange_segment.value if entity.exchange_segment else None,
            retry_count=entity.retry_count,
            error_message=entity.error_message,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class ExecutionDTO:
    id: UUID
    order_id: UUID
    quantity: str
    price: str
    commission: str
    executed_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "ExecutionDTO":
        return ExecutionDTO(
            id=entity.id,
            order_id=entity.order_id,
            quantity=str(entity.quantity),
            price=str(entity.price),
            commission=str(entity.commission),
            executed_at=entity.executed_at,
        )
