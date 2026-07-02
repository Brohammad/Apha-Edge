from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.backtesting.infrastructure.models import (
    SQLAlchemyBacktestRunRepository,
    SQLAlchemyBacktestTradeRepository,
)
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyInstrumentRepository
from alphaedge.modules.portfolio.application.commands import (
    CreatePortfolioCommand,
    GenerateRebalanceCommand,
    GetHoldingsQuery,
    GetPerformanceQuery,
    GetPortfolioQuery,
    GetRebalancePlanQuery,
    ListPortfoliosQuery,
    SyncFromBacktestCommand,
)
from alphaedge.modules.portfolio.application.handlers import (
    CreatePortfolioHandler,
    GenerateRebalanceHandler,
    GetHoldingsHandler,
    GetPerformanceHandler,
    GetPortfolioHandler,
    GetRebalancePlanHandler,
    ListPortfoliosHandler,
    SyncFromBacktestHandler,
)
from alphaedge.modules.portfolio.infrastructure.models import (
    SQLAlchemyHoldingRepository,
    SQLAlchemyPortfolioRepository,
    SQLAlchemyRebalancePlanRepository,
)
from alphaedge.modules.portfolio.presentation.schemas import (
    CreatePortfolioRequest,
    PortfolioResponse,
    RebalancePlanResponse,
    RebalanceRequest,
    SyncFromBacktestRequest,
)
from alphaedge.shared.presentation.envelope import success_response

portfolios_router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_portfolio(dto: object) -> dict:
    return PortfolioResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        name=dto.name,
        base_currency=dto.base_currency,
        initial_capital=dto.initial_capital,
        cash_balance=dto.cash_balance,
        is_paper=dto.is_paper,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


@portfolios_router.get("")
async def list_portfolios(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    repo = SQLAlchemyPortfolioRepository(session)
    handler = ListPortfoliosHandler(repo)
    items, total = await handler.handle(
        ListPortfoliosQuery(user_id=user_id, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_portfolio(i) for i in items], "total_count": total},
        request_id=_request_id(request),
    )


@portfolios_router.post("", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: CreatePortfolioRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyPortfolioRepository(session)
    handler = CreatePortfolioHandler(repo)
    dto = await handler.handle(
        CreatePortfolioCommand(
            user_id=user_id,
            name=body.name,
            initial_capital=body.initial_capital,
            base_currency=body.base_currency,
            is_paper=body.is_paper,
        )
    )
    return success_response(_to_portfolio(dto), request_id=_request_id(request))


@portfolios_router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyPortfolioRepository(session)
    handler = GetPortfolioHandler(repo)
    dto = await handler.handle(GetPortfolioQuery(user_id=user_id, portfolio_id=portfolio_id))
    return success_response(_to_portfolio(dto), request_id=_request_id(request))


@portfolios_router.get("/{portfolio_id}/holdings")
async def get_holdings(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    holding_repo = SQLAlchemyHoldingRepository(session)
    handler = GetHoldingsHandler(portfolio_repo, holding_repo)
    items = await handler.handle(GetHoldingsQuery(user_id=user_id, portfolio_id=portfolio_id))
    return success_response(
        {
            "items": [
                {
                    "id": str(i.id),
                    "portfolio_id": str(i.portfolio_id),
                    "instrument_id": str(i.instrument_id),
                    "quantity": i.quantity,
                    "avg_cost": i.avg_cost,
                    "current_price": i.current_price,
                    "market_value": i.market_value,
                    "updated_at": i.updated_at.isoformat(),
                }
                for i in items
            ],
            "total_count": len(items),
        },
        request_id=_request_id(request),
    )


@portfolios_router.get("/{portfolio_id}/performance")
async def get_performance(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    holding_repo = SQLAlchemyHoldingRepository(session)
    handler = GetPerformanceHandler(portfolio_repo, holding_repo)
    summary = await handler.handle(GetPerformanceQuery(user_id=user_id, portfolio_id=portfolio_id))
    return success_response(summary, request_id=_request_id(request))


@portfolios_router.post("/{portfolio_id}/rebalance", status_code=status.HTTP_201_CREATED)
async def generate_rebalance(
    portfolio_id: UUID,
    body: RebalanceRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    holding_repo = SQLAlchemyHoldingRepository(session)
    plan_repo = SQLAlchemyRebalancePlanRepository(session)
    instrument_repo = SQLAlchemyInstrumentRepository(session)
    handler = GenerateRebalanceHandler(portfolio_repo, holding_repo, plan_repo, instrument_repo)
    dto = await handler.handle(
        GenerateRebalanceCommand(
            user_id=user_id,
            portfolio_id=portfolio_id,
            target_allocation=body.target_allocation,
        )
    )
    return success_response(
        RebalancePlanResponse(
            id=str(dto.id),
            portfolio_id=str(dto.portfolio_id),
            target_allocation=dto.target_allocation,
            proposed_trades=dto.proposed_trades,
            status=dto.status,
            created_at=dto.created_at,
        ).model_dump(mode="json"),
        request_id=_request_id(request),
    )


@portfolios_router.get("/{portfolio_id}/rebalance/{plan_id}")
async def get_rebalance_plan(
    portfolio_id: UUID,
    plan_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    plan_repo = SQLAlchemyRebalancePlanRepository(session)
    handler = GetRebalancePlanHandler(portfolio_repo, plan_repo)
    dto = await handler.handle(
        GetRebalancePlanQuery(user_id=user_id, portfolio_id=portfolio_id, plan_id=plan_id)
    )
    return success_response(
        RebalancePlanResponse(
            id=str(dto.id),
            portfolio_id=str(dto.portfolio_id),
            target_allocation=dto.target_allocation,
            proposed_trades=dto.proposed_trades,
            status=dto.status,
            created_at=dto.created_at,
        ).model_dump(mode="json"),
        request_id=_request_id(request),
    )


@portfolios_router.post("/{portfolio_id}/sync-from-backtest")
async def sync_from_backtest(
    portfolio_id: UUID,
    body: SyncFromBacktestRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    portfolio_repo = SQLAlchemyPortfolioRepository(session)
    holding_repo = SQLAlchemyHoldingRepository(session)
    run_repo = SQLAlchemyBacktestRunRepository(session)
    trade_repo = SQLAlchemyBacktestTradeRepository(session)
    handler = SyncFromBacktestHandler(portfolio_repo, holding_repo, trade_repo, run_repo)
    items = await handler.handle(
        SyncFromBacktestCommand(
            user_id=user_id,
            portfolio_id=portfolio_id,
            backtest_run_id=UUID(body.backtest_run_id),
        )
    )
    return success_response(
        {"items": [{"instrument_id": str(i.instrument_id), "quantity": i.quantity} for i in items]},
        request_id=_request_id(request),
    )
