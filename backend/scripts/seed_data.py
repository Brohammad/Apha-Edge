"""Seed roles, instruments, and sample market data."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from alphaedge.modules.identity.domain.entities import RoleName
from alphaedge.modules.identity.infrastructure.models import RoleModel
from alphaedge.modules.market_data.domain.entities import IngestionJob, Instrument
from alphaedge.shared.infrastructure.database import async_session_factory

DEFAULT_ROLES = [
    (RoleName.ADMIN, "Full platform access"),
    (RoleName.TRADER, "Create strategies, run backtests, manage portfolios"),
    (RoleName.VIEWER, "Read-only access"),
    (RoleName.API_SERVICE, "Programmatic API access"),
]

SAMPLE_INSTRUMENTS = [
    ("AAPL", "NASDAQ", "Apple Inc."),
    ("MSFT", "NASDAQ", "Microsoft Corporation"),
    ("GOOGL", "NASDAQ", "Alphabet Inc."),
    ("SPY", "NYSE", "SPDR S&P 500 ETF Trust"),
]


async def seed_roles() -> None:
    async with async_session_factory() as session:
        for role_name, description in DEFAULT_ROLES:
            existing = await session.execute(
                select(RoleModel).where(RoleModel.name == role_name.value)
            )
            if existing.scalar_one_or_none() is None:
                session.add(
                    RoleModel(id=uuid4(), name=role_name.value, description=description)
                )
        await session.commit()


async def seed_instruments() -> None:
    async with async_session_factory() as session:
        for symbol, exchange, name in SAMPLE_INSTRUMENTS:
            existing = await session.execute(
                select(InstrumentModel).where(InstrumentModel.symbol == symbol)
            )
            if existing.scalar_one_or_none() is None:
                entity = Instrument.create(
                    symbol=symbol,
                    exchange=exchange,
                    asset_class=AssetClass.EQUITY,
                    currency="USD",
                    name=name,
                )
                session.add(
                    InstrumentModel(
                        id=entity.id,
                        symbol=entity.symbol,
                        exchange=entity.exchange,
                        asset_class=entity.asset_class.value,
                        currency=entity.currency,
                        name=entity.name,
                        is_active=True,
                        metadata_={},
                    )
                )
        await session.commit()


async def seed_sample_bars() -> None:
    end = datetime.now(UTC)
    start = end - timedelta(days=30)
    async with async_session_factory() as session:
        job = IngestionJob.create(
            provider="mock",
            symbols=[s[0] for s in SAMPLE_INSTRUMENTS],
            timeframe=Timeframe.D1,
            start_date=start,
            end_date=end,
        )
        session.add(
            IngestionJobModel(
                id=job.id,
                provider=job.provider,
                status=job.status.value,
                symbols=job.symbols,
                timeframe=job.timeframe.value,
                start_date=job.start_date,
                end_date=job.end_date,
            )
        )
        await session.commit()
        job_id = job.id

    await execute_ingestion(job_id)


async def main() -> None:
    await seed_roles()
    await seed_instruments()
    await seed_sample_bars()
    print("Seed complete: roles, instruments, and 30 days of mock bars.")


if __name__ == "__main__":
    asyncio.run(main())
