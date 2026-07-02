from datetime import datetime
from uuid import UUID

from alphaedge.modules.market_data.application.commands import (
    BarDTO,
    CreateInstrumentCommand,
    GetBarsQuery,
    GetIngestionJobQuery,
    GetInstrumentQuery,
    GetLatestBarQuery,
    IngestionJobDTO,
    InstrumentDTO,
    ListInstrumentsQuery,
    SearchInstrumentsQuery,
    TriggerIngestionCommand,
)
from alphaedge.modules.market_data.domain.entities import Instrument
from alphaedge.modules.market_data.domain.enums import IngestionStatus
from alphaedge.modules.market_data.domain.repositories import (
    BarRepository,
    IngestionJobRepository,
    InstrumentRepository,
)
from alphaedge.shared.domain.exceptions import ConflictError, NotFoundError


class CreateInstrumentHandler:
    def __init__(self, repo: InstrumentRepository) -> None:
        self._repo = repo

    async def handle(self, command: CreateInstrumentCommand) -> InstrumentDTO:
        existing = await self._repo.get_by_symbol(command.symbol)
        if existing:
            raise ConflictError(f"Instrument {command.symbol} already exists")
        instrument = Instrument.create(
            symbol=command.symbol,
            exchange=command.exchange,
            asset_class=command.asset_class,
            currency=command.currency,
            name=command.name,
            metadata=command.metadata,
        )
        saved = await self._repo.save(instrument)
        return InstrumentDTO.from_entity(saved)


class ListInstrumentsHandler:
    def __init__(self, repo: InstrumentRepository) -> None:
        self._repo = repo

    async def handle(self, query: ListInstrumentsQuery) -> tuple[list[InstrumentDTO], int]:
        items = await self._repo.list_all(
            active_only=query.active_only, limit=query.limit, offset=query.offset
        )
        total = await self._repo.count(active_only=query.active_only)
        return [InstrumentDTO.from_entity(i) for i in items], total


class SearchInstrumentsHandler:
    def __init__(self, repo: InstrumentRepository) -> None:
        self._repo = repo

    async def handle(self, query: SearchInstrumentsQuery) -> list[InstrumentDTO]:
        items = await self._repo.search(query.query, limit=query.limit)
        return [InstrumentDTO.from_entity(i) for i in items]


class GetInstrumentHandler:
    def __init__(self, repo: InstrumentRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetInstrumentQuery) -> InstrumentDTO:
        instrument = await self._repo.get_by_id(query.instrument_id)
        if not instrument:
            raise NotFoundError("Instrument", str(query.instrument_id))
        return InstrumentDTO.from_entity(instrument)


class GetBarsHandler:
    def __init__(self, instrument_repo: InstrumentRepository, bar_repo: BarRepository) -> None:
        self._instrument_repo = instrument_repo
        self._bar_repo = bar_repo

    async def handle(self, query: GetBarsQuery) -> tuple[list[BarDTO], int]:
        instrument = await self._instrument_repo.get_by_id(query.instrument_id)
        if not instrument:
            raise NotFoundError("Instrument", str(query.instrument_id))
        bars = await self._bar_repo.get_bars(
            query.instrument_id,
            query.timeframe,
            query.start,
            query.end,
            query.limit,
            query.offset,
        )
        total = await self._bar_repo.count(
            query.instrument_id, query.timeframe, query.start, query.end
        )
        return [BarDTO.from_entity(b) for b in bars], total


class GetLatestBarHandler:
    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        bar_repo: BarRepository,
        cache: "BarCache | None" = None,
    ) -> None:
        self._instrument_repo = instrument_repo
        self._bar_repo = bar_repo
        self._cache = cache

    async def handle(self, query: GetLatestBarQuery) -> BarDTO:
        instrument = await self._instrument_repo.get_by_id(query.instrument_id)
        if not instrument:
            raise NotFoundError("Instrument", str(query.instrument_id))

        if self._cache:
            cached = await self._cache.get(query.instrument_id, query.timeframe)
            if cached:
                return BarDTO.from_entity(cached)

        bar = await self._bar_repo.get_latest(query.instrument_id, query.timeframe)
        if not bar:
            raise NotFoundError("Bar", f"{query.instrument_id}/{query.timeframe.value}")

        if self._cache:
            await self._cache.set(query.instrument_id, query.timeframe, bar)

        return BarDTO.from_entity(bar)


class TriggerIngestionHandler:
    def __init__(self, job_repo: IngestionJobRepository) -> None:
        self._job_repo = job_repo

    async def handle(self, command: TriggerIngestionCommand) -> IngestionJobDTO:
        from alphaedge.modules.market_data.domain.entities import IngestionJob

        job = IngestionJob.create(
            provider=command.provider,
            symbols=command.symbols,
            timeframe=command.timeframe,
            start_date=command.start_date,
            end_date=command.end_date,
        )
        saved = await self._job_repo.save(job)

        from alphaedge.modules.market_data.infrastructure.tasks import run_ingestion_task

        task = run_ingestion_task.delay(str(saved.id))
        saved.celery_task_id = task.id
        saved.status = IngestionStatus.PENDING
        await self._job_repo.update(saved)

        return IngestionJobDTO.from_entity(saved)


class GetIngestionJobHandler:
    def __init__(self, job_repo: IngestionJobRepository) -> None:
        self._job_repo = job_repo

    async def handle(self, query: GetIngestionJobQuery) -> IngestionJobDTO:
        job = await self._job_repo.get_by_id(query.job_id)
        if not job:
            raise NotFoundError("IngestionJob", str(query.job_id))
        return IngestionJobDTO.from_entity(job)


class BarCache:
    """Redis cache for latest bars."""

    def __init__(self, redis_client: object) -> None:
        self._redis = redis_client

    def _key(self, instrument_id: UUID, timeframe: object) -> str:
        tf = timeframe.value if hasattr(timeframe, "value") else timeframe
        return f"bar:latest:{instrument_id}:{tf}"

    async def get(self, instrument_id: UUID, timeframe: object) -> object | None:
        import json
        from decimal import Decimal

        from alphaedge.modules.market_data.domain.entities import Bar
        from alphaedge.modules.market_data.domain.enums import Timeframe

        raw = await self._redis.get(self._key(instrument_id, timeframe))
        if not raw:
            return None
        data = json.loads(raw)
        return Bar(
            instrument_id=UUID(data["instrument_id"]),
            timeframe=Timeframe(data["timeframe"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=Decimal(data["open"]),
            high=Decimal(data["high"]),
            low=Decimal(data["low"]),
            close=Decimal(data["close"]),
            volume=Decimal(data["volume"]),
            vwap=Decimal(data["vwap"]) if data.get("vwap") else None,
            source=data.get("source", "cache"),
        )

    async def set(self, instrument_id: UUID, timeframe: object, bar: object) -> None:
        import json

        data = {
            "instrument_id": str(bar.instrument_id),
            "timeframe": bar.timeframe.value,
            "timestamp": bar.timestamp.isoformat(),
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": str(bar.volume),
            "vwap": str(bar.vwap) if bar.vwap else None,
            "source": bar.source,
        }
        await self._redis.set(self._key(instrument_id, timeframe), json.dumps(data), ex=300)
