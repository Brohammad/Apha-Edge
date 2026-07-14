from decimal import Decimal
from uuid import UUID

from alphaedge.config import settings
from alphaedge.modules.execution.application.commands import (
    BrokerConnectionDTO,
    CancelOrderCommand,
    CreateBrokerConnectionCommand,
    DeleteBrokerConnectionCommand,
    ExecutionDTO,
    GetOrderQuery,
    ListBrokerConnectionsQuery,
    ListExecutionsQuery,
    ListOrdersQuery,
    OrderDTO,
    SubmitOrderCommand,
)
from alphaedge.modules.execution.domain.entities import BrokerConnection, Order
from alphaedge.modules.execution.domain.enums import BrokerName, OrderEventType, OrderType
from alphaedge.modules.execution.domain.repositories import (
    BrokerConnectionRepository,
    ExecutionRepository,
    OrderEventRepository,
    OrderRepository,
)
from alphaedge.modules.execution.domain.services import record_event
from alphaedge.modules.execution.infrastructure.models import get_broker
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.repositories import BarRepository, InstrumentRepository
from alphaedge.modules.portfolio.domain.repositories import HoldingRepository, PortfolioRepository
from alphaedge.modules.risk.domain.gate import ProposedOrder, RiskGate
from alphaedge.modules.risk.domain.repositories import RiskLimitRepository, RiskSnapshotRepository
from alphaedge.shared.domain.exceptions import (
    AuthorizationError,
    NotFoundError,
    RiskRejectedError,
    ValidationError,
)
from alphaedge.shared.domain.value_objects import Side
from alphaedge.shared.infrastructure.logging import get_logger
from alphaedge.shared.infrastructure.metrics import ORDERS_SUBMITTED, RISK_GATE_REJECTIONS

logger = get_logger(__name__)


class CreateBrokerConnectionHandler:
    def __init__(self, repo: BrokerConnectionRepository) -> None:
        self._repo = repo

    async def handle(self, command: CreateBrokerConnectionCommand) -> BrokerConnectionDTO:
        try:
            broker_name = BrokerName(command.broker_name)
        except ValueError as exc:
            raise ValidationError(f"Invalid broker name: {command.broker_name}") from exc
        connection = BrokerConnection.create(
            user_id=command.user_id,
            broker_name=broker_name,
            credentials=command.credentials,
            is_paper=command.is_paper,
        )
        if not connection.is_paper and not settings.live_trading_enabled:
            raise ValidationError(
                "Live trading is disabled on this deployment. "
                "Set LIVE_TRADING_ENABLED=true after completing the production checklist."
            )
        saved = await self._repo.save(connection)
        return BrokerConnectionDTO.from_entity(saved)


class ListBrokerConnectionsHandler:
    def __init__(self, repo: BrokerConnectionRepository) -> None:
        self._repo = repo

    async def handle(self, query: ListBrokerConnectionsQuery) -> list[BrokerConnectionDTO]:
        items = await self._repo.list_by_user(query.user_id)
        return [BrokerConnectionDTO.from_entity(c) for c in items]


class DeleteBrokerConnectionHandler:
    def __init__(self, repo: BrokerConnectionRepository) -> None:
        self._repo = repo

    async def handle(self, command: DeleteBrokerConnectionCommand) -> None:
        connection = await self._repo.get_by_id(command.connection_id)
        if not connection:
            raise NotFoundError("BrokerConnection", str(command.connection_id))
        if connection.user_id != command.user_id:
            raise AuthorizationError("You do not own this broker connection")
        connection.is_active = False
        await self._repo.update(connection)


class SubmitOrderHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        connection_repo: BrokerConnectionRepository,
        portfolio_repo: PortfolioRepository,
        instrument_repo: InstrumentRepository,
        event_repo: OrderEventRepository,
        holding_repo: HoldingRepository | None = None,
        risk_limit_repo: RiskLimitRepository | None = None,
        risk_snapshot_repo: RiskSnapshotRepository | None = None,
        bar_repo: BarRepository | None = None,
    ) -> None:
        self._order_repo = order_repo
        self._connection_repo = connection_repo
        self._portfolio_repo = portfolio_repo
        self._instrument_repo = instrument_repo
        self._event_repo = event_repo
        self._holding_repo = holding_repo
        self._risk_limit_repo = risk_limit_repo
        self._risk_snapshot_repo = risk_snapshot_repo
        self._bar_repo = bar_repo

    async def handle(self, command: SubmitOrderCommand) -> OrderDTO:
        if command.idempotency_key:
            existing = await self._order_repo.get_by_idempotency_key(command.idempotency_key)
            if existing:
                return OrderDTO.from_entity(existing)

        portfolio = await self._portfolio_repo.get_by_id(command.portfolio_id)
        if not portfolio:
            raise NotFoundError("Portfolio", str(command.portfolio_id))
        if portfolio.user_id != command.user_id:
            raise AuthorizationError("You do not own this portfolio")

        connection = await self._connection_repo.get_by_id(command.broker_connection_id)
        if not connection or not connection.is_active:
            raise NotFoundError("BrokerConnection", str(command.broker_connection_id))
        if connection.user_id != command.user_id:
            raise AuthorizationError("You do not own this broker connection")

        if not connection.is_paper:
            if not settings.live_trading_enabled:
                raise ValidationError("Live trading is disabled on this deployment")
            if not command.live_trading_acknowledged:
                raise ValidationError(
                    "Live orders require live_trading_acknowledged=true in the request body"
                )
            if portfolio.is_paper:
                raise ValidationError("Cannot route live orders through a paper portfolio")

        instrument = await self._instrument_repo.get_by_id(command.instrument_id)
        if not instrument:
            raise NotFoundError("Instrument", str(command.instrument_id))

        try:
            side = Side(command.side.lower())
        except ValueError as exc:
            raise ValidationError(f"Invalid side: {command.side}") from exc
        try:
            order_type = OrderType(command.order_type.lower())
        except ValueError as exc:
            raise ValidationError(f"Invalid order type: {command.order_type}") from exc

        limit_price = Decimal(command.limit_price) if command.limit_price else None
        stop_price = Decimal(command.stop_price) if command.stop_price else None
        quantity = Decimal(command.quantity)

        await self._enforce_risk_gate(
            portfolio=portfolio,
            instrument_id=command.instrument_id,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
        )

        order = Order.create(
            portfolio_id=command.portfolio_id,
            broker_connection_id=command.broker_connection_id,
            instrument_id=command.instrument_id,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            idempotency_key=command.idempotency_key,
        )
        saved = await self._order_repo.save(order)
        await self._event_repo.save(record_event(saved, OrderEventType.CREATED))
        ORDERS_SUBMITTED.labels(side=side.value, order_type=order_type.value).inc()
        return OrderDTO.from_entity(saved)

    async def _enforce_risk_gate(
        self,
        *,
        portfolio,
        instrument_id: UUID,
        side: Side,
        quantity: Decimal,
        limit_price: Decimal | None,
    ) -> None:
        if not self._holding_repo or not self._risk_limit_repo:
            return

        holdings = await self._holding_repo.list_by_portfolio(portfolio.id)

        estimated_price = limit_price
        if estimated_price is None and self._bar_repo is not None:
            bar = await self._bar_repo.get_latest(instrument_id, Timeframe.D1)
            if bar is not None:
                estimated_price = bar.close

        limits = await self._risk_limit_repo.list_by_portfolio(portfolio.id)
        snapshot = None
        if self._risk_snapshot_repo is not None:
            snapshot = await self._risk_snapshot_repo.get_latest(portfolio.id)

        if estimated_price is None:
            held = next((h for h in holdings if h.instrument_id == instrument_id), None)
            if held and held.current_price > 0:
                estimated_price = held.current_price

        if estimated_price is None:
            # Still run cash/sell sizing checks with a sentinel rejection when no price.
            decision = RiskGate.evaluate(
                portfolio=portfolio,
                holdings=holdings,
                proposed=ProposedOrder(
                    instrument_id=instrument_id,
                    side=side,
                    quantity=quantity,
                    estimated_price=Decimal("0"),
                ),
                limits=limits,
                latest_snapshot=snapshot,
            )
        else:
            decision = RiskGate.evaluate(
                portfolio=portfolio,
                holdings=holdings,
                proposed=ProposedOrder(
                    instrument_id=instrument_id,
                    side=side,
                    quantity=quantity,
                    estimated_price=estimated_price,
                ),
                limits=limits,
                latest_snapshot=snapshot,
            )

        if not decision.allowed:
            stage = decision.stage or "unknown"
            RISK_GATE_REJECTIONS.labels(stage=stage).inc()
            logger.warning(
                "risk_gate_rejected",
                portfolio_id=str(portfolio.id),
                instrument_id=str(instrument_id),
                side=side.value,
                quantity=str(quantity),
                stage=stage,
                reason=decision.reason,
            )
            raise RiskRejectedError(
                decision.reason or "Order rejected by risk gate",
                stage=decision.stage,
            )


class ListOrdersHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        portfolio_repo: PortfolioRepository,
    ) -> None:
        self._order_repo = order_repo
        self._portfolio_repo = portfolio_repo

    async def handle(self, query: ListOrdersQuery) -> tuple[list[OrderDTO], int]:
        if query.portfolio_id:
            portfolio = await self._portfolio_repo.get_by_id(query.portfolio_id)
            if not portfolio:
                raise NotFoundError("Portfolio", str(query.portfolio_id))
            if portfolio.user_id != query.user_id:
                raise AuthorizationError("You do not own this portfolio")
            items = await self._order_repo.list_by_portfolio(
                query.portfolio_id, limit=query.limit, offset=query.offset
            )
            total = await self._order_repo.count_by_portfolio(query.portfolio_id)
            return [OrderDTO.from_entity(o) for o in items], total

        portfolios = await self._portfolio_repo.list_by_user(query.user_id, limit=200, offset=0)
        portfolio_ids = [p.id for p in portfolios]
        # Fetch enough rows in one query to paginate without N+1 per portfolio.
        fetch_limit = max(query.offset + query.limit, query.limit)
        orders = await self._order_repo.list_by_portfolio_ids(portfolio_ids, limit=fetch_limit)
        all_orders = [OrderDTO.from_entity(o) for o in orders]
        page = all_orders[query.offset : query.offset + query.limit]
        return page, len(all_orders)


class GetOrderHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        portfolio_repo: PortfolioRepository,
    ) -> None:
        self._order_repo = order_repo
        self._portfolio_repo = portfolio_repo

    async def handle(self, query: GetOrderQuery) -> OrderDTO:
        order = await _get_owned_order(
            self._order_repo, self._portfolio_repo, query.user_id, query.order_id
        )
        return OrderDTO.from_entity(order)


class CancelOrderHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        portfolio_repo: PortfolioRepository,
        connection_repo: BrokerConnectionRepository,
        event_repo: OrderEventRepository,
    ) -> None:
        self._order_repo = order_repo
        self._portfolio_repo = portfolio_repo
        self._connection_repo = connection_repo
        self._event_repo = event_repo

    async def handle(self, command: CancelOrderCommand) -> OrderDTO:
        order = await _get_owned_order(
            self._order_repo, self._portfolio_repo, command.user_id, command.order_id
        )
        if not order.can_cancel():
            raise ValidationError(f"Cannot cancel order in status {order.status.value}")

        connection = await self._connection_repo.get_by_id(order.broker_connection_id)
        if connection:
            broker = get_broker(connection)
            await broker.cancel_order(order)

        order.mark_cancelled()
        updated = await self._order_repo.update(order)
        await self._event_repo.save(record_event(updated, OrderEventType.CANCELLED))
        portfolio = await self._portfolio_repo.get_by_id(order.portfolio_id)
        if portfolio:
            from alphaedge.modules.execution.infrastructure.order_pubsub import publish_order_update

            await publish_order_update(
                user_id=portfolio.user_id,
                order_id=updated.id,
                portfolio_id=updated.portfolio_id,
                status=updated.status.value,
                filled_quantity=str(updated.filled_quantity),
                event_type="cancelled",
            )
        return OrderDTO.from_entity(updated)


class ListExecutionsHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        portfolio_repo: PortfolioRepository,
        execution_repo: ExecutionRepository,
    ) -> None:
        self._order_repo = order_repo
        self._portfolio_repo = portfolio_repo
        self._execution_repo = execution_repo

    async def handle(self, query: ListExecutionsQuery) -> list[ExecutionDTO]:
        await _get_owned_order(
            self._order_repo, self._portfolio_repo, query.user_id, query.order_id
        )
        executions = await self._execution_repo.list_by_order_id(query.order_id)
        return [ExecutionDTO.from_entity(e) for e in executions]


async def _get_owned_order(
    order_repo: OrderRepository,
    portfolio_repo: PortfolioRepository,
    user_id: UUID,
    order_id: UUID,
) -> Order:
    order = await order_repo.get_by_id(order_id)
    if not order:
        raise NotFoundError("Order", str(order_id))
    portfolio = await portfolio_repo.get_by_id(order.portfolio_id)
    if not portfolio or portfolio.user_id != user_id:
        raise AuthorizationError("You do not own this order")
    return order
