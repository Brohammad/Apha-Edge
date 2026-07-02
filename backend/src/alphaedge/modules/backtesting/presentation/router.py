from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.backtesting.application.commands import (
    DeleteBacktestRunCommand,
    GetBacktestResultQuery,
    GetBacktestRunQuery,
    GetBacktestTradesQuery,
    GetEquityCurveQuery,
    ListBacktestRunsQuery,
    SubmitBacktestCommand,
)
from alphaedge.modules.backtesting.application.handlers import (
    DeleteBacktestRunHandler,
    GetBacktestResultHandler,
    GetBacktestRunHandler,
    GetBacktestTradesHandler,
    GetEquityCurveHandler,
    ListBacktestRunsHandler,
    SubmitBacktestHandler,
)
from alphaedge.modules.backtesting.infrastructure.models import (
    SQLAlchemyBacktestResultRepository,
    SQLAlchemyBacktestRunRepository,
    SQLAlchemyBacktestTradeRepository,
)
from alphaedge.modules.backtesting.infrastructure.tasks import run_backtest_task
from alphaedge.modules.backtesting.presentation.schemas import (
    BacktestResultResponse,
    BacktestRunResponse,
    BacktestTradeResponse,
    SubmitBacktestRequest,
)
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.presentation.envelope import success_response

backtest_router = APIRouter(prefix="/backtest-runs", tags=["Backtesting"])


def _repos(session: AsyncSession):
    return (
        SQLAlchemyBacktestRunRepository(session),
        SQLAlchemyBacktestResultRepository(session),
        SQLAlchemyBacktestTradeRepository(session),
        SQLAlchemyStrategyRepository(session),
        SQLAlchemyStrategyVersionRepository(session),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_run(dto: object) -> dict:
    return BacktestRunResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        strategy_version_id=str(dto.strategy_version_id),
        name=dto.name,
        status=dto.status,
        config=dto.config,
        started_at=dto.started_at,
        completed_at=dto.completed_at,
        error_message=dto.error_message,
        celery_task_id=dto.celery_task_id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_result(dto: object) -> dict:
    return BacktestResultResponse(
        id=str(dto.id),
        backtest_run_id=str(dto.backtest_run_id),
        total_return=dto.total_return,
        annualized_return=dto.annualized_return,
        sharpe_ratio=dto.sharpe_ratio,
        sortino_ratio=dto.sortino_ratio,
        max_drawdown=dto.max_drawdown,
        win_rate=dto.win_rate,
        total_trades=dto.total_trades,
        profit_factor=dto.profit_factor,
        metrics=dto.metrics,
    ).model_dump(mode="json")


def _to_trade(dto: object) -> dict:
    return BacktestTradeResponse(
        id=str(dto.id),
        instrument_id=str(dto.instrument_id),
        side=dto.side,
        quantity=dto.quantity,
        entry_price=dto.entry_price,
        exit_price=dto.exit_price,
        entry_time=dto.entry_time,
        exit_time=dto.exit_time,
        pnl=dto.pnl,
        commission=dto.commission,
        slippage=dto.slippage,
    ).model_dump(mode="json")


@backtest_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_backtest(
    body: SubmitBacktestRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, strategy_repo, version_repo = _repos(session)
    handler = SubmitBacktestHandler(run_repo, strategy_repo, version_repo)
    result = await handler.handle(
        SubmitBacktestCommand(
            user_id=user_id,
            strategy_version_id=UUID(body.strategy_version_id),
            name=body.name,
            config=body.config,
        )
    )

    task = run_backtest_task.delay(str(result.id))
    run_entity = await run_repo.get_by_id(result.id)
    if run_entity:
        run_entity.celery_task_id = task.id
        await run_repo.update(run_entity)

    return success_response(_to_run(result), request_id=_request_id(request))


@backtest_router.get("")
async def list_backtest_runs(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, _, _ = _repos(session)
    handler = ListBacktestRunsHandler(run_repo)
    items, total = await handler.handle(
        ListBacktestRunsQuery(user_id=user_id, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_run(r) for r in items], "total_count": total},
        request_id=_request_id(request),
    )


@backtest_router.get("/{run_id}")
async def get_backtest_run(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, _, _ = _repos(session)
    handler = GetBacktestRunHandler(run_repo)
    result = await handler.handle(GetBacktestRunQuery(user_id=user_id, run_id=run_id))
    return success_response(_to_run(result), request_id=_request_id(request))


@backtest_router.get("/{run_id}/result")
async def get_backtest_result(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, result_repo, _, _, _ = _repos(session)
    handler = GetBacktestResultHandler(run_repo, result_repo)
    result = await handler.handle(GetBacktestResultQuery(user_id=user_id, run_id=run_id))
    return success_response(_to_result(result), request_id=_request_id(request))


@backtest_router.get("/{run_id}/trades")
async def get_backtest_trades(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, trade_repo, _, _ = _repos(session)
    handler = GetBacktestTradesHandler(run_repo, trade_repo)
    items = await handler.handle(GetBacktestTradesQuery(user_id=user_id, run_id=run_id))
    return success_response(
        {"items": [_to_trade(t) for t in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@backtest_router.get("/{run_id}/equity-curve")
async def get_equity_curve(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, result_repo, _, _, _ = _repos(session)
    handler = GetEquityCurveHandler(run_repo, result_repo)
    curve = await handler.handle(GetEquityCurveQuery(user_id=user_id, run_id=run_id))
    return success_response(
        {"items": curve, "total_count": len(curve)},
        request_id=_request_id(request),
    )


@backtest_router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, _, _ = _repos(session)
    handler = DeleteBacktestRunHandler(run_repo)
    await handler.handle(DeleteBacktestRunCommand(user_id=user_id, run_id=run_id))
