from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.portfolio.infrastructure.models import (
    SQLAlchemyHoldingRepository,
    SQLAlchemyPortfolioRepository,
)
from alphaedge.modules.risk.application.commands import (
    ComputeRiskCommand,
    GetLatestRiskSnapshotQuery,
    GetRiskLimitsQuery,
    ListRiskSnapshotsQuery,
    UpdateRiskLimitsCommand,
)
from alphaedge.modules.risk.application.handlers import (
    ComputeRiskHandler,
    GetLatestRiskSnapshotHandler,
    GetRiskLimitsHandler,
    ListRiskSnapshotsHandler,
    UpdateRiskLimitsHandler,
)
from alphaedge.modules.risk.infrastructure.models import (
    SQLAlchemyRiskLimitRepository,
    SQLAlchemyRiskSnapshotRepository,
)
from alphaedge.modules.risk.presentation.schemas import (
    RiskLimitResponse,
    RiskSnapshotResponse,
    UpdateRiskLimitsRequest,
)
from alphaedge.shared.presentation.envelope import success_response

risk_router = APIRouter(prefix="/portfolios", tags=["Risk"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_snapshot(dto: object) -> dict:
    return RiskSnapshotResponse(
        id=str(dto.id),
        portfolio_id=str(dto.portfolio_id),
        snapshot_at=dto.snapshot_at,
        var_95=dto.var_95,
        var_99=dto.var_99,
        max_drawdown=dto.max_drawdown,
        sharpe_ratio=dto.sharpe_ratio,
        sortino_ratio=dto.sortino_ratio,
        beta=dto.beta,
        alpha=dto.alpha,
        volatility=dto.volatility,
        correlation_matrix=dto.correlation_matrix,
        metrics=dto.metrics,
        violations=dto.violations,
    ).model_dump(mode="json")


@risk_router.post("/{portfolio_id}/risk/compute", status_code=status.HTTP_201_CREATED)
async def compute_risk(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = ComputeRiskHandler(
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyHoldingRepository(session),
        SQLAlchemyRiskSnapshotRepository(session),
        SQLAlchemyRiskLimitRepository(session),
        session,
    )
    dto = await handler.handle(ComputeRiskCommand(user_id=user_id, portfolio_id=portfolio_id))
    return success_response(_to_snapshot(dto), request_id=_request_id(request))


@risk_router.get("/{portfolio_id}/risk/snapshots")
async def list_risk_snapshots(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    handler = ListRiskSnapshotsHandler(
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyRiskSnapshotRepository(session),
    )
    items, total = await handler.handle(
        ListRiskSnapshotsQuery(
            user_id=user_id, portfolio_id=portfolio_id, limit=limit, offset=offset
        )
    )
    return success_response(
        {"items": [_to_snapshot(i) for i in items], "total_count": total},
        request_id=_request_id(request),
    )


@risk_router.get("/{portfolio_id}/risk/snapshots/latest")
async def get_latest_risk_snapshot(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = GetLatestRiskSnapshotHandler(
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyRiskSnapshotRepository(session),
    )
    dto = await handler.handle(
        GetLatestRiskSnapshotQuery(user_id=user_id, portfolio_id=portfolio_id)
    )
    return success_response(_to_snapshot(dto), request_id=_request_id(request))


@risk_router.get("/{portfolio_id}/risk/limits")
async def get_risk_limits(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = GetRiskLimitsHandler(
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyRiskLimitRepository(session),
    )
    items = await handler.handle(GetRiskLimitsQuery(user_id=user_id, portfolio_id=portfolio_id))
    return success_response(
        {
            "items": [
                RiskLimitResponse(
                    id=str(i.id),
                    portfolio_id=str(i.portfolio_id),
                    limit_type=i.limit_type,
                    threshold=i.threshold,
                    is_active=i.is_active,
                ).model_dump(mode="json")
                for i in items
            ]
        },
        request_id=_request_id(request),
    )


@risk_router.put("/{portfolio_id}/risk/limits")
async def update_risk_limits(
    portfolio_id: UUID,
    body: UpdateRiskLimitsRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = UpdateRiskLimitsHandler(
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyRiskLimitRepository(session),
    )
    items = await handler.handle(
        UpdateRiskLimitsCommand(
            user_id=user_id,
            portfolio_id=portfolio_id,
            limits=[item.model_dump() for item in body.limits],
        )
    )
    return success_response(
        {
            "items": [
                RiskLimitResponse(
                    id=str(i.id),
                    portfolio_id=str(i.portfolio_id),
                    limit_type=i.limit_type,
                    threshold=i.threshold,
                    is_active=i.is_active,
                ).model_dump(mode="json")
                for i in items
            ]
        },
        request_id=_request_id(request),
    )
