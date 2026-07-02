import asyncio
from datetime import UTC, datetime
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Instrument
from alphaedge.modules.market_data.domain.enums import AssetClass, IngestionStatus
from alphaedge.modules.market_data.domain.services import BarNormalizer
from alphaedge.modules.market_data.infrastructure.models import (
    SQLAlchemyBarRepository,
    SQLAlchemyIngestionJobRepository,
    SQLAlchemyInstrumentRepository,
)
from alphaedge.modules.market_data.infrastructure.providers import get_provider
from alphaedge.shared.infrastructure.database import async_session_factory


async def execute_ingestion(job_id: UUID) -> None:
    async with async_session_factory() as session:
        job_repo = SQLAlchemyIngestionJobRepository(session)
        instrument_repo = SQLAlchemyInstrumentRepository(session)
        bar_repo = SQLAlchemyBarRepository(session)

        job = await job_repo.get_by_id(job_id)
        if not job:
            return

        job.status = IngestionStatus.RUNNING
        job.started_at = datetime.now(UTC)
        await job_repo.update(job)
        await session.commit()

        try:
            provider = get_provider(job.provider)
            total_records = 0

            for symbol in job.symbols:
                instrument = await instrument_repo.get_by_symbol(symbol)
                if not instrument:
                    instrument = Instrument.create(
                        symbol=symbol,
                        exchange="UNKNOWN",
                        asset_class=AssetClass.EQUITY,
                        currency="USD",
                        name=symbol,
                    )
                    instrument = await instrument_repo.save(instrument)

                raw_bars = await provider.fetch_bars(
                    symbol, job.timeframe, job.start_date, job.end_date
                )
                domain_bars = [
                    BarNormalizer.to_domain(raw, instrument.id, job.timeframe, provider.name)
                    for raw in raw_bars
                ]
                total_records += await bar_repo.upsert_many(domain_bars)

            job.status = IngestionStatus.COMPLETED
            job.records_count = total_records
            job.completed_at = datetime.now(UTC)
            await job_repo.update(job)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            job = await job_repo.get_by_id(job_id)
            if job:
                job.status = IngestionStatus.FAILED
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(UTC)
                await job_repo.update(job)
                await session.commit()
            raise


def run_ingestion_sync(job_id: str) -> None:
    asyncio.run(execute_ingestion(UUID(job_id)))
