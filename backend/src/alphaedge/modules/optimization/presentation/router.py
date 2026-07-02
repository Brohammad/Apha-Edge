from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.optimization.application.commands import (
    GetBestTrialQuery,
    GetOptimizationRunQuery,
    ListOptimizationRunsQuery,
    ListOptimizationTrialsQuery,
    SubmitOptimizationCommand,
)
from alphaedge.modules.optimization.application.handlers import (
    GetBestTrialHandler,
    GetOptimizationRunHandler,
    ListOptimizationRunsHandler,
    ListOptimizationTrialsHandler,
    SubmitOptimizationHandler,
)
from alphaedge.modules.optimization.infrastructure.models import (
    SQLAlchemyOptimizationRunRepository,
    SQLAlchemyOptimizationTrialRepository,
)
from alphaedge.modules.optimization.infrastructure.tasks import run_optimization_task
from alphaedge.modules.optimization.presentation.schemas import (
    OptimizationRunResponse,
    OptimizationTrialResponse,
    SubmitOptimizationRequest,
)
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.presentation.envelope import success_response

optimization_router = APIRouter(prefix="/optimization-runs", tags=["Optimization"])


def _repos(session: AsyncSession):
    return (
        SQLAlchemyOptimizationRunRepository(session),
        SQLAlchemyOptimizationTrialRepository(session),
        SQLAlchemyStrategyRepository(session),
        SQLAlchemyStrategyVersionRepository(session),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_run(dto: object) -> dict:
    return OptimizationRunResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        strategy_version_id=str(dto.strategy_version_id),
        name=dto.name,
        method=dto.method,
        objective=dto.objective,
        parameter_space=dto.parameter_space,
        backtest_config=dto.backtest_config,
        walk_forward_config=dto.walk_forward_config,
        status=dto.status,
        best_trial_id=str(dto.best_trial_id) if dto.best_trial_id else None,
        total_trials=dto.total_trials,
        completed_trials=dto.completed_trials,
        started_at=dto.started_at,
        completed_at=dto.completed_at,
        error_message=dto.error_message,
        celery_task_id=dto.celery_task_id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_trial(dto: object) -> dict:
    return OptimizationTrialResponse(
        id=str(dto.id),
        optimization_run_id=str(dto.optimization_run_id),
        backtest_run_id=str(dto.backtest_run_id) if dto.backtest_run_id else None,
        parameters=dto.parameters,
        objective_value=dto.objective_value,
        in_sample_objective=dto.in_sample_objective,
        window_index=dto.window_index,
        rank=dto.rank,
        status=dto.status,
        created_at=dto.created_at,
    ).model_dump(mode="json")


@optimization_router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_optimization(
    body: SubmitOptimizationRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, strategy_repo, version_repo = _repos(session)
    handler = SubmitOptimizationHandler(run_repo, strategy_repo, version_repo)
    result = await handler.handle(
        SubmitOptimizationCommand(
            user_id=user_id,
            strategy_version_id=UUID(body.strategy_version_id),
            name=body.name,
            method=body.method,
            objective=body.objective,
            parameter_space=body.parameter_space,
            backtest_config=body.backtest_config,
            walk_forward_config=body.walk_forward_config,
        )
    )

    task = run_optimization_task.delay(str(result.id))
    run_entity = await run_repo.get_by_id(result.id)
    if run_entity:
        run_entity.celery_task_id = task.id
        await run_repo.update(run_entity)

    return success_response(_to_run(result), request_id=_request_id(request))


@optimization_router.get("")
async def list_optimization_runs(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, _ = _repos(session)
    handler = ListOptimizationRunsHandler(run_repo)
    items, total = await handler.handle(
        ListOptimizationRunsQuery(user_id=user_id, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_run(r) for r in items], "total_count": total},
        request_id=_request_id(request),
    )


@optimization_router.get("/{run_id}")
async def get_optimization_run(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, _, _, _ = _repos(session)
    handler = GetOptimizationRunHandler(run_repo)
    result = await handler.handle(GetOptimizationRunQuery(user_id=user_id, run_id=run_id))
    return success_response(_to_run(result), request_id=_request_id(request))


@optimization_router.get("/{run_id}/trials")
async def list_optimization_trials(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, trial_repo, _, _ = _repos(session)
    handler = ListOptimizationTrialsHandler(run_repo, trial_repo)
    items = await handler.handle(ListOptimizationTrialsQuery(user_id=user_id, run_id=run_id))
    return success_response(
        {"items": [_to_trial(t) for t in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@optimization_router.get("/{run_id}/best")
async def get_best_trial(
    run_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    run_repo, trial_repo, _, _ = _repos(session)
    handler = GetBestTrialHandler(run_repo, trial_repo)
    result = await handler.handle(GetBestTrialQuery(user_id=user_id, run_id=run_id))
    return success_response(_to_trial(result), request_id=_request_id(request))
