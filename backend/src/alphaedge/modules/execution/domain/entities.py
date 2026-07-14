from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.execution.domain.enums import (
    BrokerName,
    ExchangeSegment,
    OrderEventType,
    OrderStatus,
    OrderType,
    ProductType,
)
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.domain.value_objects import Side


@dataclass
class BrokerConnection:
    id: UUID
    user_id: UUID
    broker_name: BrokerName
    credentials: dict[str, object]
    is_paper: bool
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        broker_name: BrokerName,
        *,
        credentials: dict[str, object] | None = None,
        is_paper: bool = True,
    ) -> "BrokerConnection":
        return BrokerConnection(
            id=uuid4(),
            user_id=user_id,
            broker_name=broker_name,
            credentials=credentials or {},
            is_paper=is_paper,
            is_active=True,
        )


@dataclass
class Order:
    id: UUID
    portfolio_id: UUID
    broker_connection_id: UUID
    instrument_id: UUID
    side: Side
    order_type: OrderType
    quantity: Decimal
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    broker_order_id: str | None = None
    idempotency_key: str | None = None
    product_type: ProductType = ProductType.CNC
    exchange_segment: ExchangeSegment | None = None
    retry_count: int = 0
    celery_task_id: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        portfolio_id: UUID,
        broker_connection_id: UUID,
        instrument_id: UUID,
        side: Side,
        order_type: OrderType,
        quantity: Decimal,
        *,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
        idempotency_key: str | None = None,
        product_type: ProductType = ProductType.CNC,
        exchange_segment: ExchangeSegment | None = None,
    ) -> "Order":
        if quantity <= 0:
            raise ValidationError("Order quantity must be positive")
        if order_type == OrderType.LIMIT and limit_price is None:
            raise ValidationError("limit_price is required for limit orders")
        if order_type == OrderType.STOP and stop_price is None:
            raise ValidationError("stop_price is required for stop orders")
        return Order(
            id=uuid4(),
            portfolio_id=portfolio_id,
            broker_connection_id=broker_connection_id,
            instrument_id=instrument_id,
            side=side,
            order_type=order_type,
            quantity=quantity,
            status=OrderStatus.PENDING,
            limit_price=limit_price,
            stop_price=stop_price,
            idempotency_key=idempotency_key,
            product_type=product_type,
            exchange_segment=exchange_segment,
        )

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    def can_cancel(self) -> bool:
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        )

    def mark_submitted(self, broker_order_id: str) -> None:
        self.status = OrderStatus.SUBMITTED
        self.broker_order_id = broker_order_id
        self.updated_at = datetime.now(UTC)

    def apply_fill(self, fill_qty: Decimal) -> None:
        if fill_qty <= 0:
            raise ValidationError("Fill quantity must be positive")
        self.filled_quantity += fill_qty
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        self.updated_at = datetime.now(UTC)

    def mark_cancelled(self) -> None:
        if not self.can_cancel():
            raise ValidationError(f"Cannot cancel order in status {self.status.value}")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(UTC)

    def mark_rejected(self, reason: str) -> None:
        self.status = OrderStatus.REJECTED
        self.error_message = reason[:2000]
        self.updated_at = datetime.now(UTC)


@dataclass
class Execution:
    id: UUID
    order_id: UUID
    quantity: Decimal
    price: Decimal
    commission: Decimal
    executed_at: datetime

    @staticmethod
    def create(
        order_id: UUID,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        *,
        executed_at: datetime | None = None,
    ) -> "Execution":
        return Execution(
            id=uuid4(),
            order_id=order_id,
            quantity=quantity,
            price=price,
            commission=commission,
            executed_at=executed_at or datetime.now(UTC),
        )


@dataclass
class OrderEvent:
    id: UUID
    order_id: UUID
    event_type: OrderEventType
    payload: dict[str, object]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        order_id: UUID,
        event_type: OrderEventType,
        payload: dict[str, object] | None = None,
    ) -> "OrderEvent":
        return OrderEvent(
            id=uuid4(),
            order_id=order_id,
            event_type=event_type,
            payload=payload or {},
        )
