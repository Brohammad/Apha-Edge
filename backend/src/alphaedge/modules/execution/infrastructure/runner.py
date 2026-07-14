import asyncio
from uuid import UUID

from alphaedge.modules.execution.domain.broker import BrokerInstrument
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderEventType, OrderStatus
from alphaedge.modules.execution.domain.services import (
    PortfolioUpdater,
    record_event,
    record_execution,
)
from alphaedge.modules.execution.infrastructure.alpaca_broker import BrokerError
from alphaedge.modules.execution.infrastructure.models import (
    SQLAlchemyBrokerConnectionRepository,
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderEventRepository,
    SQLAlchemyOrderRepository,
)
from alphaedge.modules.execution.infrastructure.registry import get_broker
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.infrastructure.models import (
    SQLAlchemyBarRepository,
    SQLAlchemyInstrumentRepository,
)
from alphaedge.modules.portfolio.infrastructure.models import (
    SQLAlchemyHoldingRepository,
    SQLAlchemyPortfolioRepository,
)
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.infrastructure.database import async_session_factory


class TransientOrderError(Exception):
    """Raised when order processing should be retried."""


async def _notify_order_update(user_id: UUID | None, order: Order, event_type: str) -> None:
    if user_id is None:
        return
    from alphaedge.modules.execution.infrastructure.order_pubsub import publish_order_update

    await publish_order_update(
        user_id=user_id,
        order_id=order.id,
        portfolio_id=order.portfolio_id,
        status=order.status.value,
        filled_quantity=str(order.filled_quantity),
        event_type=event_type,
    )


async def execute_order(order_id: UUID) -> None:
    notify_user_id: UUID | None = None
    async with async_session_factory() as session:
        order_repo = SQLAlchemyOrderRepository(session)
        connection_repo = SQLAlchemyBrokerConnectionRepository(session)
        execution_repo = SQLAlchemyExecutionRepository(session)
        event_repo = SQLAlchemyOrderEventRepository(session)
        portfolio_repo = SQLAlchemyPortfolioRepository(session)
        holding_repo = SQLAlchemyHoldingRepository(session)
        bar_repo = SQLAlchemyBarRepository(session)
        instrument_repo = SQLAlchemyInstrumentRepository(session)

        order = await order_repo.get_by_id(order_id)
        if not order:
            return
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return

        portfolio_meta = await portfolio_repo.get_by_id(order.portfolio_id)
        notify_user_id = portfolio_meta.user_id if portfolio_meta else None

        connection = await connection_repo.get_by_id(order.broker_connection_id)
        if not connection or not connection.is_active:
            order.mark_rejected("Broker connection inactive or not found")
            await order_repo.update(order)
            await event_repo.save(
                record_event(order, OrderEventType.REJECTED, {"reason": order.error_message})
            )
            await session.commit()
            await _notify_order_update(notify_user_id, order, "rejected")
            return

        instrument = await instrument_repo.get_by_id(order.instrument_id)
        if instrument is None:
            order.mark_rejected("Instrument not found")
            await order_repo.update(order)
            await event_repo.save(
                record_event(order, OrderEventType.REJECTED, {"reason": "instrument_not_found"})
            )
            await session.commit()
            await _notify_order_update(notify_user_id, order, "rejected")
            return

        bar = await bar_repo.get_latest(order.instrument_id, Timeframe.D1)
        if bar is None:
            order.retry_count += 1
            await order_repo.update(order)
            await event_repo.save(
                record_event(order, OrderEventType.RETRY, {"reason": "no_market_data"})
            )
            await session.commit()
            raise TransientOrderError("No market data available for instrument")

        broker_instrument = BrokerInstrument(
            symbol=instrument.symbol,
            exchange=instrument.exchange,
            currency=instrument.currency,
            metadata=instrument.metadata,
        )
        broker = get_broker(connection)

        try:
            ack = await broker.submit_order(order, broker_instrument, bar.close)
        except BrokerError as exc:
            order.mark_rejected(str(exc))
            await order_repo.update(order)
            await event_repo.save(
                record_event(order, OrderEventType.REJECTED, {"reason": str(exc)})
            )
            await session.commit()
            await _notify_order_update(notify_user_id, order, "rejected")
            return
        if order.status == OrderStatus.PENDING:
            order.mark_submitted(ack.broker_order_id)
            await order_repo.update(order)
            await event_repo.save(record_event(order, OrderEventType.SUBMITTED))

        if ack.fill is None:
            await session.commit()
            await _notify_order_update(notify_user_id, order, "submitted")
            if order.order_type.value == "market":
                raise TransientOrderError("Market order received no fill")
            return

        portfolio = portfolio_meta or await portfolio_repo.get_by_id(order.portfolio_id)
        if not portfolio:
            order.mark_rejected("Portfolio not found")
            await order_repo.update(order)
            await session.commit()
            await _notify_order_update(notify_user_id, order, "rejected")
            return

        holding = await holding_repo.get_by_portfolio_and_instrument(
            order.portfolio_id, order.instrument_id
        )

        try:
            updated_holding = PortfolioUpdater.apply_fill(
                portfolio,
                holding,
                instrument_id=order.instrument_id,
                side=order.side,
                quantity=ack.fill.filled_quantity,
                price=ack.fill.fill_price,
                commission=ack.fill.commission,
            )
        except ValidationError as exc:
            order.mark_rejected(str(exc))
            await order_repo.update(order)
            await event_repo.save(
                record_event(order, OrderEventType.REJECTED, {"reason": str(exc)})
            )
            await session.commit()
            await _notify_order_update(notify_user_id, order, "rejected")
            return

        order.apply_fill(ack.fill.filled_quantity)
        await order_repo.update(order)

        execution = record_execution(
            order,
            ack.fill.filled_quantity,
            ack.fill.fill_price,
            ack.fill.commission,
        )
        await execution_repo.save(execution)

        event_type = (
            OrderEventType.FILLED
            if order.status == OrderStatus.FILLED
            else OrderEventType.PARTIAL_FILL
        )
        await event_repo.save(
            record_event(
                order,
                event_type,
                {
                    "quantity": str(ack.fill.filled_quantity),
                    "price": str(ack.fill.fill_price),
                    "commission": str(ack.fill.commission),
                },
            )
        )

        await portfolio_repo.update(portfolio)
        if updated_holding is not None:
            if updated_holding.quantity > 0:
                await holding_repo.upsert(updated_holding)
            elif holding is not None:
                await holding_repo.delete(holding.id)

        await session.commit()
        await _notify_order_update(notify_user_id, order, event_type.value)


def run_order_sync(order_id: str) -> None:
    asyncio.run(execute_order(UUID(order_id)))
