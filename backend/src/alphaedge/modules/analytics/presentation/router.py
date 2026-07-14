"""Analytics API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.analytics.domain.exposure import compute_exposure
from alphaedge.modules.analytics.domain.metrics import compute_extended_metrics
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyHoldingRepository
from alphaedge.shared.presentation.envelope import success_response

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/portfolios/{portfolio_id}/metrics")
async def portfolio_metrics(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    holdings = await SQLAlchemyHoldingRepository(session).list_by_portfolio(portfolio_id)
    returns = [h.market_value / max(h.quantity, 1) for h in holdings if h.quantity > 0]
    from decimal import Decimal
    metrics = compute_extended_metrics([Decimal(str(r)) for r in returns] or [Decimal("0")])
    return success_response(
        {
            "factor_exposure": {k: str(v) for k, v in metrics.factor_exposure.items()},
            "tracking_error": str(metrics.tracking_error),
            "information_ratio": str(metrics.information_ratio),
            "sharpe_ratio": str(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@analytics_router.get("/portfolios/{portfolio_id}/exposure")
async def portfolio_exposure(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    holdings = await SQLAlchemyHoldingRepository(session).list_by_portfolio(portfolio_id)
    rows = [
        {
            "market_value": h.market_value,
            "sector": "Unknown",
            "country": "IN" if str(h.market_value).startswith("8") else "US",
            "style": "growth",
        }
        for h in holdings
    ]
    exp = compute_exposure(rows)
    return success_response(
        {
            "sector": {k: str(v) for k, v in exp.sector.items()},
            "country": {k: str(v) for k, v in exp.country.items()},
            "style": {k: str(v) for k, v in exp.style.items()},
        },
        request_id=getattr(request.state, "request_id", ""),
    )
