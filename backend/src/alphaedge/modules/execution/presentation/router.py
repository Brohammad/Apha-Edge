from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.config import settings
from alphaedge.dependencies import get_current_user_id, get_db_session, require_verified_email
from alphaedge.modules.execution.application.commands import (
    CancelOrderCommand,
    CreateBrokerConnectionCommand,
    DeleteBrokerConnectionCommand,
    GetOrderQuery,
    ListBrokerConnectionsQuery,
    ListExecutionsQuery,
    ListOrdersQuery,
    SubmitOrderCommand,
)
from alphaedge.modules.execution.application.handlers import (
    CancelOrderHandler,
    CreateBrokerConnectionHandler,
    DeleteBrokerConnectionHandler,
    GetOrderHandler,
    ListBrokerConnectionsHandler,
    ListExecutionsHandler,
    ListOrdersHandler,
    SubmitOrderHandler,
)
from alphaedge.modules.execution.infrastructure.models import (
    SQLAlchemyBrokerConnectionRepository,
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderEventRepository,
    SQLAlchemyOrderRepository,
)
from alphaedge.modules.execution.infrastructure.tasks import process_order_task
from alphaedge.modules.execution.presentation.schemas import (
    BrokerConnectionResponse,
    CreateBrokerConnectionRequest,
    ExecutionResponse,
    OrderResponse,
    SubmitOrderRequest,
)
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyInstrumentRepository
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyPortfolioRepository
from alphaedge.shared.infrastructure.audit import record_audit
from alphaedge.shared.presentation.envelope import success_response

broker_connections_router = APIRouter(prefix="/broker-connections", tags=["Execution"])
orders_router = APIRouter(prefix="/orders", tags=["Execution"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_connection(dto: object) -> dict:
    return BrokerConnectionResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        broker_name=dto.broker_name,
        is_paper=dto.is_paper,
        is_active=dto.is_active,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_order(dto: object) -> dict:
    return OrderResponse(
        id=str(dto.id),
        portfolio_id=str(dto.portfolio_id),
        broker_connection_id=str(dto.broker_connection_id),
        instrument_id=str(dto.instrument_id),
        side=dto.side,
        order_type=dto.order_type,
        quantity=dto.quantity,
        filled_quantity=dto.filled_quantity,
        limit_price=dto.limit_price,
        stop_price=dto.stop_price,
        status=dto.status,
        broker_order_id=dto.broker_order_id,
        idempotency_key=dto.idempotency_key,
        retry_count=dto.retry_count,
        error_message=dto.error_message,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_execution(dto: object) -> dict:
    return ExecutionResponse(
        id=str(dto.id),
        order_id=str(dto.order_id),
        quantity=dto.quantity,
        price=dto.price,
        commission=dto.commission,
        executed_at=dto.executed_at,
    ).model_dump(mode="json")


@broker_connections_router.get("/live-trading/status")
async def live_trading_status(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
):
    return success_response(
        {
            "live_trading_enabled": settings.live_trading_enabled,
        },
        request_id=_request_id(request),
    )


@broker_connections_router.get("")
async def list_broker_connections(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyBrokerConnectionRepository(session)
    handler = ListBrokerConnectionsHandler(repo)
    items = await handler.handle(ListBrokerConnectionsQuery(user_id=user_id))
    return success_response(
        {"items": [_to_connection(c) for c in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@broker_connections_router.post("", status_code=status.HTTP_201_CREATED)
async def create_broker_connection(
    body: CreateBrokerConnectionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    _verified: object = Depends(require_verified_email),
):
    repo = SQLAlchemyBrokerConnectionRepository(session)
    handler = CreateBrokerConnectionHandler(repo)
    result = await handler.handle(
        CreateBrokerConnectionCommand(
            user_id=user_id,
            broker_name=body.broker_name,
            credentials=body.credentials,
            is_paper=body.is_paper,
        )
    )
    await record_audit(
        session,
        user_id=user_id,
        action="broker_connection.create",
        resource_type="broker_connection",
        resource_id=result.id,
        request=request,
        changes={"broker_name": body.broker_name, "is_paper": body.is_paper},
    )
    return success_response(_to_connection(result), request_id=_request_id(request))


@broker_connections_router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broker_connection(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyBrokerConnectionRepository(session)
    handler = DeleteBrokerConnectionHandler(repo)
    await handler.handle(
        DeleteBrokerConnectionCommand(user_id=user_id, connection_id=connection_id)
    )


@orders_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_order(
    body: SubmitOrderRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    _verified: object = Depends(require_verified_email),
):
    order_repo = SQLAlchemyOrderRepository(session)
    connection_repo = SQLAlchemyBrokerConnectionRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    instrument_repo = SQLAlchemyInstrumentRepository(session)
    event_repo = SQLAlchemyOrderEventRepository(session)
    handler = SubmitOrderHandler(
        order_repo, connection_repo, portfolio_repo, instrument_repo, event_repo
    )
    result = await handler.handle(
        SubmitOrderCommand(
            user_id=user_id,
            portfolio_id=UUID(body.portfolio_id),
            broker_connection_id=UUID(body.broker_connection_id),
            instrument_id=UUID(body.instrument_id),
            side=body.side,
            order_type=body.order_type,
            quantity=body.quantity,
            limit_price=body.limit_price,
            stop_price=body.stop_price,
            idempotency_key=body.idempotency_key,
            live_trading_acknowledged=body.live_trading_acknowledged,
        )
    )

    task = process_order_task.delay(str(result.id))
    order_entity = await order_repo.get_by_id(result.id)
    if order_entity:
        order_entity.celery_task_id = task.id
        await order_repo.update(order_entity)

    await record_audit(
        session,
        user_id=user_id,
        action="order.submit",
        resource_type="order",
        resource_id=result.id,
        request=request,
        changes={"side": body.side, "quantity": str(body.quantity)},
    )

    return success_response(_to_order(result), request_id=_request_id(request))


@orders_router.get("")
async def list_orders(
    request: Request,
    portfolio_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    order_repo = SQLAlchemyOrderRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    handler = ListOrdersHandler(order_repo, portfolio_repo)
    items, total = await handler.handle(
        ListOrdersQuery(
            user_id=user_id,
            portfolio_id=portfolio_id,
            limit=limit,
            offset=offset,
        )
    )
    return success_response(
        {"items": [_to_order(o) for o in items], "total_count": total},
        request_id=_request_id(request),
    )


@orders_router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    order_repo = SQLAlchemyOrderRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    handler = GetOrderHandler(order_repo, portfolio_repo)
    result = await handler.handle(GetOrderQuery(user_id=user_id, order_id=order_id))
    return success_response(_to_order(result), request_id=_request_id(request))


@orders_router.delete("/{order_id}", status_code=status.HTTP_200_OK)
async def cancel_order(
    order_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    order_repo = SQLAlchemyOrderRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    connection_repo = SQLAlchemyBrokerConnectionRepository(session)
    event_repo = SQLAlchemyOrderEventRepository(session)
    handler = CancelOrderHandler(order_repo, portfolio_repo, connection_repo, event_repo)
    result = await handler.handle(CancelOrderCommand(user_id=user_id, order_id=order_id))
    return success_response(_to_order(result), request_id=_request_id(request))


@orders_router.get("/{order_id}/executions")
async def list_executions(
    order_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    order_repo = SQLAlchemyOrderRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    execution_repo = SQLAlchemyExecutionRepository(session)
    handler = ListExecutionsHandler(order_repo, portfolio_repo, execution_repo)
    items = await handler.handle(ListExecutionsQuery(user_id=user_id, order_id=order_id))
    return success_response(
        {"items": [_to_execution(e) for e in items], "total_count": len(items)},
        request_id=_request_id(request),
    )
