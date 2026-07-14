from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session, require_admin
from alphaedge.modules.market_data.application.commands import (
    CreateInstrumentCommand,
    GetBarsQuery,
    GetIngestionJobQuery,
    GetInstrumentQuery,
    GetLatestBarQuery,
    ListInstrumentsQuery,
    SearchInstrumentsQuery,
    TriggerIngestionCommand,
)
from alphaedge.modules.market_data.application.handlers import (
    BarCache,
    CreateInstrumentHandler,
    GetBarsHandler,
    GetIngestionJobHandler,
    GetInstrumentHandler,
    GetLatestBarHandler,
    ListInstrumentsHandler,
    SearchInstrumentsHandler,
    TriggerIngestionHandler,
)
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.option_chain import build_option_chain
from alphaedge.modules.market_data.infrastructure.models import (
    SQLAlchemyBarRepository,
    SQLAlchemyIngestionJobRepository,
    SQLAlchemyInstrumentRepository,
)
from alphaedge.modules.market_data.infrastructure.quotes import QuoteCache, QuoteService
from alphaedge.modules.market_data.presentation.schemas import (
    BarResponse,
    CreateInstrumentRequest,
    IngestionJobResponse,
    InstrumentResponse,
    OptionChainResponse,
    OptionContractResponse,
    QuoteResponse,
    TriggerIngestionRequest,
)
from alphaedge.shared.infrastructure.redis import get_redis
from alphaedge.shared.presentation.envelope import success_response

instruments_router = APIRouter(prefix="/instruments", tags=["Market Data"])
market_data_router = APIRouter(prefix="/market-data", tags=["Market Data"])


def _repos(session: AsyncSession):
    return (
        SQLAlchemyInstrumentRepository(session),
        SQLAlchemyBarRepository(session),
        SQLAlchemyIngestionJobRepository(session),
    )


def _to_instrument(dto: object) -> dict:
    return InstrumentResponse(
        id=str(dto.id),
        symbol=dto.symbol,
        exchange=dto.exchange,
        asset_class=dto.asset_class,
        currency=dto.currency,
        name=dto.name,
        is_active=dto.is_active,
    ).model_dump()


def _to_bar(dto: object) -> dict:
    return BarResponse(
        instrument_id=str(dto.instrument_id),
        timeframe=dto.timeframe,
        timestamp=dto.timestamp,
        open=dto.open,
        high=dto.high,
        low=dto.low,
        close=dto.close,
        volume=dto.volume,
        vwap=dto.vwap,
        source=dto.source,
    ).model_dump()


def _to_job(dto: object) -> dict:
    return IngestionJobResponse(
        id=str(dto.id),
        provider=dto.provider,
        status=dto.status,
        symbols=dto.symbols,
        timeframe=dto.timeframe,
        start_date=dto.start_date,
        end_date=dto.end_date,
        records_count=dto.records_count,
        error_message=dto.error_message,
        celery_task_id=dto.celery_task_id,
        started_at=dto.started_at,
        completed_at=dto.completed_at,
    ).model_dump()


@instruments_router.get("")
async def list_instruments(
    request: Request,
    active_only: bool = True,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    instrument_repo, _, _ = _repos(session)
    if q:
        handler = SearchInstrumentsHandler(instrument_repo)
        items = await handler.handle(SearchInstrumentsQuery(query=q, limit=limit))
        return success_response(
            {"items": [_to_instrument(i) for i in items], "total_count": len(items)},
            request_id=_request_id(request),
        )
    handler = ListInstrumentsHandler(instrument_repo)
    items, total = await handler.handle(
        ListInstrumentsQuery(active_only=active_only, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_instrument(i) for i in items], "total_count": total},
        request_id=_request_id(request),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@instruments_router.post("", status_code=201)
async def create_instrument(
    body: CreateInstrumentRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _admin: object = Depends(require_admin),
):
    instrument_repo, _, _ = _repos(session)
    handler = CreateInstrumentHandler(instrument_repo)
    result = await handler.handle(
        CreateInstrumentCommand(
            symbol=body.symbol,
            exchange=body.exchange,
            asset_class=body.asset_class,
            currency=body.currency,
            name=body.name,
            metadata=body.metadata,
        )
    )
    return success_response(_to_instrument(result), request_id=_request_id(request))


@instruments_router.get("/{instrument_id}")
async def get_instrument(
    instrument_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    instrument_repo, _, _ = _repos(session)
    handler = GetInstrumentHandler(instrument_repo)
    result = await handler.handle(GetInstrumentQuery(instrument_id=instrument_id))
    return success_response(_to_instrument(result), request_id=_request_id(request))


@instruments_router.get("/{instrument_id}/bars")
async def get_bars(
    instrument_id: UUID,
    request: Request,
    timeframe: Timeframe = Timeframe.D1,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    instrument_repo, bar_repo, _ = _repos(session)
    handler = GetBarsHandler(instrument_repo, bar_repo)
    items, total = await handler.handle(
        GetBarsQuery(
            instrument_id=instrument_id,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )
    )
    return success_response(
        {"items": [_to_bar(b) for b in items], "total_count": total},
        request_id=_request_id(request),
    )


@instruments_router.get("/{instrument_id}/bars/latest")
async def get_latest_bar(
    instrument_id: UUID,
    request: Request,
    timeframe: Timeframe = Timeframe.D1,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    instrument_repo, bar_repo, _ = _repos(session)
    redis = await get_redis()
    cache = BarCache(redis)
    handler = GetLatestBarHandler(instrument_repo, bar_repo, cache)
    query = GetLatestBarQuery(instrument_id=instrument_id, timeframe=timeframe)
    result = await handler.handle(query)
    return success_response(_to_bar(result), request_id=_request_id(request))


@market_data_router.get("/quotes")
async def get_quotes(
    request: Request,
    symbols: str = Query(description="Comma-separated symbols, e.g. AAPL,MSFT"),
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    instrument_repo, bar_repo, _ = _repos(session)
    redis = await get_redis()
    service = QuoteService(instrument_repo, bar_repo, QuoteCache(redis))
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    quotes = await service.get_quotes(symbol_list)
    return success_response(
        {
            "items": [
                QuoteResponse(
                    symbol=q.symbol,
                    price=str(q.price),
                    change_pct=str(q.change_pct) if q.change_pct is not None else None,
                    as_of=q.as_of,
                    source=q.source,
                    fallback_reason=q.fallback_reason,
                ).model_dump()
                for q in quotes
            ]
        },
        request_id=_request_id(request),
    )


@market_data_router.get("/options/{symbol}/chain")
async def get_option_chain(
    symbol: str,
    request: Request,
    spot: float | None = Query(default=None, description="Override spot price"),
    _user_id: UUID = Depends(get_current_user_id),
):
    from decimal import Decimal

    spot_price = Decimal(str(spot)) if spot is not None else None
    chain = build_option_chain(symbol, spot_price)
    payload = OptionChainResponse(
        underlying=chain.underlying,
        spot_price=str(chain.spot_price),
        as_of=chain.as_of,
        contracts=[
            OptionContractResponse(
                symbol=c.symbol,
                strike=str(c.strike),
                option_type=c.option_type,
                expiry=c.expiry.isoformat(),
                ltp=str(c.ltp),
                oi=c.oi,
                iv=str(c.iv) if c.iv is not None else None,
            )
            for c in chain.contracts
        ],
    )
    return success_response(payload.model_dump(mode="json"), request_id=_request_id(request))


@market_data_router.post("/ingest", status_code=202)
async def trigger_ingestion(
    body: TriggerIngestionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _admin: object = Depends(require_admin),
):
    _, _, job_repo = _repos(session)
    handler = TriggerIngestionHandler(job_repo)
    result = await handler.handle(
        TriggerIngestionCommand(
            provider=body.provider,
            symbols=body.symbols,
            timeframe=body.timeframe,
            start_date=body.start_date,
            end_date=body.end_date,
        )
    )
    return success_response(_to_job(result), request_id=_request_id(request))


@market_data_router.get("/ingest/{job_id}")
async def get_ingestion_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    _, _, job_repo = _repos(session)
    handler = GetIngestionJobHandler(job_repo)
    result = await handler.handle(GetIngestionJobQuery(job_id=job_id))
    return success_response(_to_job(result), request_id=_request_id(request))
