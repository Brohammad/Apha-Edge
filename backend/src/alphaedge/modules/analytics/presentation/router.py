"""Analytics API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.analytics.domain.exposure import compute_exposure
from alphaedge.modules.analytics.domain.metrics import compute_extended_metrics
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyInstrumentRepository
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyHoldingRepository
from alphaedge.shared.presentation.envelope import success_response

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Exchange → ISO country when we have no instrument metadata.
_EXCHANGE_COUNTRY: dict[str, str] = {
    "NSE": "IN",
    "BSE": "IN",
    "NYSE": "US",
    "NASDAQ": "US",
    "AMEX": "US",
    "ARCA": "US",
    "BATS": "US",
    "LSE": "GB",
    "TSX": "CA",
}

_CURRENCY_COUNTRY: dict[str, str] = {
    "INR": "IN",
    "USD": "US",
    "GBP": "GB",
    "CAD": "CA",
    "EUR": "EU",
}


def _country_for_instrument(exchange: str, currency: str, metadata: dict[str, str]) -> str:
    if meta := metadata.get("country"):
        return meta.upper()
    ex = exchange.upper().strip()
    if ex in _EXCHANGE_COUNTRY:
        return _EXCHANGE_COUNTRY[ex]
    cur = currency.upper().strip()
    return _CURRENCY_COUNTRY.get(cur, "Unclassified")


@analytics_router.get("/portfolios/{portfolio_id}/metrics")
async def portfolio_metrics(
    portfolio_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    # Holdings are a point-in-time snapshot — not a returns series. Do not invent factors.
    _ = await SQLAlchemyHoldingRepository(session).list_by_portfolio(portfolio_id)
    metrics = compute_extended_metrics([])
    return success_response(
        {
            "factor_exposure": {k: str(v) for k, v in metrics.factor_exposure.items()},
            "tracking_error": str(metrics.tracking_error),
            "information_ratio": str(metrics.information_ratio),
            "sharpe_ratio": str(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
            "available": False,
            "reason": (
                "Extended metrics require a historical portfolio return series; "
                "holdings snapshots alone are insufficient."
            ),
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
    instrument_ids = list({h.instrument_id for h in holdings})
    instruments = await SQLAlchemyInstrumentRepository(session).list_by_ids(instrument_ids)
    by_id = {i.id: i for i in instruments}

    rows = []
    for h in holdings:
        instrument = by_id.get(h.instrument_id)
        metadata = instrument.metadata if instrument else {}
        sector = metadata.get("sector") or "Unclassified"
        style = metadata.get("style") or "Unclassified"
        if instrument:
            country = _country_for_instrument(
                instrument.exchange, instrument.currency, metadata
            )
        else:
            country = "Unclassified"
        rows.append(
            {
                "market_value": h.market_value,
                "sector": sector,
                "country": country,
                "style": style,
            }
        )

    exp = compute_exposure(rows)
    return success_response(
        {
            "sector": {k: str(v) for k, v in exp.sector.items()},
            "country": {k: str(v) for k, v in exp.country.items()},
            "style": {k: str(v) for k, v in exp.style.items()},
            "classification": "exchange_currency_metadata",
            "note": (
                "Sector/style require instrument metadata; otherwise Unclassified. "
                "Country is derived from metadata, exchange, or currency — never from price."
            ),
        },
        request_id=getattr(request.state, "request_id", ""),
    )
