from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar, Instrument
from alphaedge.modules.market_data.domain.enums import AssetClass, IngestionStatus, Timeframe


@dataclass(frozen=True)
class CreateInstrumentCommand:
    symbol: str
    exchange: str
    asset_class: AssetClass
    currency: str
    name: str
    metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class TriggerIngestionCommand:
    provider: str
    symbols: list[str]
    timeframe: Timeframe
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ListInstrumentsQuery:
    active_only: bool = True
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class SearchInstrumentsQuery:
    query: str
    limit: int = 20


@dataclass(frozen=True)
class GetInstrumentQuery:
    instrument_id: UUID


@dataclass(frozen=True)
class GetBarsQuery:
    instrument_id: UUID
    timeframe: Timeframe
    start: datetime | None
    end: datetime | None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetLatestBarQuery:
    instrument_id: UUID
    timeframe: Timeframe


@dataclass(frozen=True)
class GetIngestionJobQuery:
    job_id: UUID


@dataclass(frozen=True)
class InstrumentDTO:
    id: UUID
    symbol: str
    exchange: str
    asset_class: str
    currency: str
    name: str
    is_active: bool

    @staticmethod
    def from_entity(entity: Instrument) -> "InstrumentDTO":
        return InstrumentDTO(
            id=entity.id,
            symbol=entity.symbol,
            exchange=entity.exchange,
            asset_class=entity.asset_class.value,
            currency=entity.currency,
            name=entity.name,
            is_active=entity.is_active,
        )


@dataclass(frozen=True)
class BarDTO:
    instrument_id: UUID
    timeframe: str
    timestamp: datetime
    open: str
    high: str
    low: str
    close: str
    volume: str
    vwap: str | None
    source: str

    @staticmethod
    def from_entity(entity: Bar) -> "BarDTO":
        return BarDTO(
            instrument_id=entity.instrument_id,
            timeframe=entity.timeframe.value,
            timestamp=entity.timestamp,
            open=str(entity.open),
            high=str(entity.high),
            low=str(entity.low),
            close=str(entity.close),
            volume=str(entity.volume),
            vwap=str(entity.vwap) if entity.vwap is not None else None,
            source=entity.source,
        )


@dataclass(frozen=True)
class IngestionJobDTO:
    id: UUID
    provider: str
    status: str
    symbols: list[str]
    timeframe: str
    start_date: datetime
    end_date: datetime
    records_count: int
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None

    @staticmethod
    def from_entity(entity: object) -> "IngestionJobDTO":
        from alphaedge.modules.market_data.domain.entities import IngestionJob

        job = entity if isinstance(entity, IngestionJob) else entity
        return IngestionJobDTO(
            id=job.id,
            provider=job.provider,
            status=job.status.value if isinstance(job.status, IngestionStatus) else job.status,
            symbols=job.symbols,
            timeframe=job.timeframe.value
            if isinstance(job.timeframe, Timeframe)
            else job.timeframe,
            start_date=job.start_date,
            end_date=job.end_date,
            records_count=job.records_count,
            error_message=job.error_message,
            celery_task_id=job.celery_task_id,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
