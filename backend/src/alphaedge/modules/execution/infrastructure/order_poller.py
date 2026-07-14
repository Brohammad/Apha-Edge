"""Poll broker APIs for async order fill updates."""

import asyncio
from uuid import UUID

from alphaedge.modules.execution.domain.enums import OrderEventType, OrderStatus
from alphaedge.modules.execution.infrastructure.models import (
    SQLAlchemyBrokerConnectionRepository,
    SQLAlchemyOrderEventRepository,
    SQLAlchemyOrderRepository,
)
from alphaedge.modules.execution.infrastructure.registry import get_broker
from alphaedge.modules.execution.infrastructure.runner import execute_order
from alphaedge.shared.infrastructure.celery_app import celery_app
from alphaedge.shared.infrastructure.database import async_session_factory


@celery_app.task(name="execution.poll_order_status")
def poll_order_status_task(order_id: str) -> None:
    asyncio.run(_poll_order_status(UUID(order_id)))


async def _poll_order_status(order_id: UUID) -> None:
    async with async_session_factory() as session:
        order_repo = SQLAlchemyOrderRepository(session)
        connection_repo = SQLAlchemyBrokerConnectionRepository(session)
        event_repo = SQLAlchemyOrderEventRepository(session)

        order = await order_repo.get_by_id(order_id)
        if not order or order.status not in (OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED):
            return
        connection = await connection_repo.get_by_id(order.broker_connection_id)
        if not connection:
            return
        broker = get_broker(connection)
        ack = await broker.get_order_status(order)
        if ack is None or ack.fill is None:
            return
    await execute_order(order_id)
