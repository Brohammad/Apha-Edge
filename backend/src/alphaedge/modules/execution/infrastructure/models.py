from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.config import settings
from alphaedge.modules.execution.domain.entities import (
    BrokerConnection,
    Execution,
    Order,
    OrderEvent,
)
from alphaedge.modules.execution.domain.enums import (
    BrokerName,
    OrderEventType,
    OrderStatus,
    OrderType,
)
from alphaedge.modules.execution.domain.repositories import (
    BrokerConnectionRepository,
    ExecutionRepository,
    OrderEventRepository,
    OrderRepository,
)
from alphaedge.shared.domain.value_objects import Side
from alphaedge.shared.infrastructure.crypto import decrypt_json, encrypt_json
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from alphaedge.shared.infrastructure.db_timing import observe_db


class BrokerConnectionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "broker_connections"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    broker_name: Mapped[str] = mapped_column(nullable=False)
    credentials: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    is_paper: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class OrderModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "orders"

    portfolio_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    broker_connection_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    side: Mapped[str] = mapped_column(nullable=False)
    order_type: Mapped[str] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    limit_price: Mapped[Decimal | None] = mapped_column(nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default=OrderStatus.PENDING.value, index=True)
    broker_order_id: Mapped[str | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    celery_task_id: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)


class ExecutionModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "executions"

    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(nullable=False)
    commission: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderEventModel(Base):
    __tablename__ = "order_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


def _connection_to_entity(m: BrokerConnectionModel) -> BrokerConnection:
    credentials = decrypt_json(dict(m.credentials), settings.credentials_encryption_key)
    return BrokerConnection(
        id=m.id,
        user_id=m.user_id,
        broker_name=BrokerName(m.broker_name),
        credentials=credentials,
        is_paper=m.is_paper,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _order_to_entity(m: OrderModel) -> Order:
    return Order(
        id=m.id,
        portfolio_id=m.portfolio_id,
        broker_connection_id=m.broker_connection_id,
        instrument_id=m.instrument_id,
        side=Side(m.side),
        order_type=OrderType(m.order_type),
        quantity=m.quantity,
        status=OrderStatus(m.status),
        filled_quantity=m.filled_quantity,
        limit_price=m.limit_price,
        stop_price=m.stop_price,
        broker_order_id=m.broker_order_id,
        idempotency_key=m.idempotency_key,
        retry_count=m.retry_count,
        celery_task_id=m.celery_task_id,
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _execution_to_entity(m: ExecutionModel) -> Execution:
    return Execution(
        id=m.id,
        order_id=m.order_id,
        quantity=m.quantity,
        price=m.price,
        commission=m.commission,
        executed_at=m.executed_at,
    )


def _event_to_entity(m: OrderEventModel) -> OrderEvent:
    return OrderEvent(
        id=m.id,
        order_id=m.order_id,
        event_type=OrderEventType(m.event_type),
        payload=m.payload,
        created_at=m.created_at,
    )


class SQLAlchemyBrokerConnectionRepository(BrokerConnectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, connection: BrokerConnection) -> BrokerConnection:
        stored_credentials = encrypt_json(
            connection.credentials, settings.credentials_encryption_key
        )
        model = BrokerConnectionModel(
            id=connection.id,
            user_id=connection.user_id,
            broker_name=connection.broker_name.value,
            credentials=stored_credentials,
            is_paper=connection.is_paper,
            is_active=connection.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return _connection_to_entity(model)

    async def get_by_id(self, connection_id: UUID) -> BrokerConnection | None:
        model = await self._session.get(BrokerConnectionModel, connection_id)
        return _connection_to_entity(model) if model else None

    async def list_by_user(self, user_id: UUID) -> list[BrokerConnection]:
        stmt = (
            select(BrokerConnectionModel)
            .where(BrokerConnectionModel.user_id == user_id)
            .order_by(BrokerConnectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_connection_to_entity(m) for m in result.scalars().all()]

    async def update(self, connection: BrokerConnection) -> BrokerConnection:
        model = await self._session.get(BrokerConnectionModel, connection.id)
        if not model:
            raise ValueError(f"BrokerConnection {connection.id} not found")
        model.is_active = connection.is_active
        model.credentials = encrypt_json(
            connection.credentials, settings.credentials_encryption_key
        )
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _connection_to_entity(model)


class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @observe_db("order.save")
    async def save(self, order: Order) -> Order:
        model = OrderModel(
            id=order.id,
            portfolio_id=order.portfolio_id,
            broker_connection_id=order.broker_connection_id,
            instrument_id=order.instrument_id,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            status=order.status.value,
            broker_order_id=order.broker_order_id,
            idempotency_key=order.idempotency_key,
            retry_count=order.retry_count,
            celery_task_id=order.celery_task_id,
            error_message=order.error_message,
        )
        self._session.add(model)
        await self._session.flush()
        return _order_to_entity(model)

    @observe_db("order.get_by_id")
    async def get_by_id(self, order_id: UUID) -> Order | None:
        model = await self._session.get(OrderModel, order_id)
        return _order_to_entity(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        stmt = select(OrderModel).where(OrderModel.idempotency_key == key)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _order_to_entity(model) if model else None

    async def list_by_portfolio(
        self, portfolio_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.portfolio_id == portfolio_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_order_to_entity(m) for m in result.scalars().all()]

    async def list_by_portfolio_ids(
        self, portfolio_ids: list[UUID], *, limit: int = 200
    ) -> list[Order]:
        if not portfolio_ids:
            return []
        stmt = (
            select(OrderModel)
            .where(OrderModel.portfolio_id.in_(portfolio_ids))
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_order_to_entity(m) for m in result.scalars().all()]

    async def count_by_portfolio(self, portfolio_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OrderModel)
            .where(OrderModel.portfolio_id == portfolio_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    @observe_db("order.update")
    async def update(self, order: Order) -> Order:
        model = await self._session.get(OrderModel, order.id)
        if not model:
            raise ValueError(f"Order {order.id} not found")
        model.status = order.status.value
        model.filled_quantity = order.filled_quantity
        model.broker_order_id = order.broker_order_id
        model.retry_count = order.retry_count
        model.celery_task_id = order.celery_task_id
        model.error_message = order.error_message
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _order_to_entity(model)


class SQLAlchemyExecutionRepository(ExecutionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, execution: Execution) -> Execution:
        model = ExecutionModel(
            id=execution.id,
            order_id=execution.order_id,
            quantity=execution.quantity,
            price=execution.price,
            commission=execution.commission,
            executed_at=execution.executed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _execution_to_entity(model)

    async def list_by_order_id(self, order_id: UUID) -> list[Execution]:
        stmt = (
            select(ExecutionModel)
            .where(ExecutionModel.order_id == order_id)
            .order_by(ExecutionModel.executed_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_execution_to_entity(m) for m in result.scalars().all()]


class SQLAlchemyOrderEventRepository(OrderEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: OrderEvent) -> OrderEvent:
        model = OrderEventModel(
            id=event.id,
            order_id=event.order_id,
            event_type=event.event_type.value,
            payload=event.payload,
        )
        self._session.add(model)
        await self._session.flush()
        return _event_to_entity(model)

    async def list_by_order_id(self, order_id: UUID) -> list[OrderEvent]:
        stmt = (
            select(OrderEventModel)
            .where(OrderEventModel.order_id == order_id)
            .order_by(OrderEventModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_event_to_entity(m) for m in result.scalars().all()]
