from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.market_data.domain.entities import Bar, IngestionJob, Instrument
from alphaedge.modules.market_data.domain.enums import AssetClass, IngestionStatus, Timeframe
from alphaedge.modules.market_data.domain.repositories import (
    BarRepository,
    IngestionJobRepository,
    InstrumentRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InstrumentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), default="")
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_: Mapped[dict[str, str]] = mapped_column("metadata", JSONB, default=dict)


class BarModel(Base):
    __tablename__ = "bars"

    instrument_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(10), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="mock")


class IngestionJobModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "data_ingestion_jobs"

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    symbols: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    records_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _instrument_to_entity(model: InstrumentModel) -> Instrument:
    return Instrument(
        id=model.id,
        symbol=model.symbol,
        exchange=model.exchange,
        asset_class=AssetClass(model.asset_class),
        currency=model.currency,
        name=model.name,
        is_active=model.is_active,
        metadata=model.metadata_ or {},
    )


def _bar_to_entity(model: BarModel) -> Bar:
    return Bar(
        instrument_id=model.instrument_id,
        timeframe=Timeframe(model.timeframe),
        timestamp=model.timestamp,
        open=model.open,
        high=model.high,
        low=model.low,
        close=model.close,
        volume=model.volume,
        vwap=model.vwap,
        source=model.source,
    )


def _job_to_entity(model: IngestionJobModel) -> IngestionJob:
    return IngestionJob(
        id=model.id,
        provider=model.provider,
        status=IngestionStatus(model.status),
        symbols=model.symbols,
        timeframe=Timeframe(model.timeframe),
        start_date=model.start_date,
        end_date=model.end_date,
        records_count=model.records_count,
        error_message=model.error_message,
        celery_task_id=model.celery_task_id,
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
    )


class SQLAlchemyInstrumentRepository(InstrumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, instrument_id: UUID) -> Instrument | None:
        result = await self._session.get(InstrumentModel, instrument_id)
        return _instrument_to_entity(result) if result else None

    async def get_by_symbol(self, symbol: str) -> Instrument | None:
        stmt = select(InstrumentModel).where(InstrumentModel.symbol == symbol.upper())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _instrument_to_entity(model) if model else None

    async def list_all(
        self, *, active_only: bool = True, limit: int = 100, offset: int = 0
    ) -> list[Instrument]:
        stmt = select(InstrumentModel).order_by(InstrumentModel.symbol).limit(limit).offset(offset)
        if active_only:
            stmt = stmt.where(InstrumentModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_instrument_to_entity(m) for m in result.scalars()]

    async def search(self, query: str, limit: int = 20) -> list[Instrument]:
        pattern = f"%{query.upper()}%"
        stmt = (
            select(InstrumentModel)
            .where(
                InstrumentModel.is_active.is_(True),
                InstrumentModel.symbol.ilike(pattern) | InstrumentModel.name.ilike(pattern),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_instrument_to_entity(m) for m in result.scalars()]

    async def save(self, instrument: Instrument) -> Instrument:
        model = InstrumentModel(
            id=instrument.id,
            symbol=instrument.symbol,
            exchange=instrument.exchange,
            asset_class=instrument.asset_class.value,
            currency=instrument.currency,
            name=instrument.name,
            is_active=instrument.is_active,
            metadata_=instrument.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return instrument

    async def count(self, *, active_only: bool = True) -> int:
        stmt = select(func.count()).select_from(InstrumentModel)
        if active_only:
            stmt = stmt.where(InstrumentModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return int(result.scalar_one())


class SQLAlchemyBarRepository(BarRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, bars: list[Bar]) -> int:
        if not bars:
            return 0
        for bar in bars:
            model = BarModel(
                instrument_id=bar.instrument_id,
                timeframe=bar.timeframe.value,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                vwap=bar.vwap,
                source=bar.source,
            )
            await self._session.merge(model)
        await self._session.flush()
        return len(bars)

    async def get_bars(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Bar]:
        stmt = (
            select(BarModel)
            .where(
                BarModel.instrument_id == instrument_id,
                BarModel.timeframe == timeframe.value,
            )
            .order_by(BarModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        if start:
            stmt = stmt.where(BarModel.timestamp >= start)
        if end:
            stmt = stmt.where(BarModel.timestamp <= end)
        result = await self._session.execute(stmt)
        return [_bar_to_entity(m) for m in result.scalars()]

    async def get_latest(self, instrument_id: UUID, timeframe: Timeframe) -> Bar | None:
        stmt = (
            select(BarModel)
            .where(
                BarModel.instrument_id == instrument_id,
                BarModel.timeframe == timeframe.value,
            )
            .order_by(BarModel.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _bar_to_entity(model) if model else None

    async def count(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(BarModel)
            .where(
                BarModel.instrument_id == instrument_id,
                BarModel.timeframe == timeframe.value,
            )
        )
        if start:
            stmt = stmt.where(BarModel.timestamp >= start)
        if end:
            stmt = stmt.where(BarModel.timestamp <= end)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())


class SQLAlchemyIngestionJobRepository(IngestionJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        result = await self._session.get(IngestionJobModel, job_id)
        return _job_to_entity(result) if result else None

    async def save(self, job: IngestionJob) -> IngestionJob:
        model = IngestionJobModel(
            id=job.id,
            provider=job.provider,
            status=job.status.value,
            symbols=job.symbols,
            timeframe=job.timeframe.value,
            start_date=job.start_date,
            end_date=job.end_date,
            records_count=job.records_count,
            error_message=job.error_message,
            celery_task_id=job.celery_task_id,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return job

    async def update(self, job: IngestionJob) -> IngestionJob:
        model = await self._session.get(IngestionJobModel, job.id)
        if not model:
            raise ValueError(f"Job {job.id} not found")
        model.status = job.status.value
        model.records_count = job.records_count
        model.error_message = job.error_message
        model.celery_task_id = job.celery_task_id
        model.started_at = job.started_at
        model.completed_at = job.completed_at
        await self._session.flush()
        return job
