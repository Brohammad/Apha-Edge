import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.engine import BacktestEngine
from alphaedge.modules.backtesting.domain.enums import BacktestStatus
from alphaedge.modules.backtesting.infrastructure.models import (
    SQLAlchemyBacktestResultRepository,
    SQLAlchemyBacktestRunRepository,
    SQLAlchemyBacktestTradeRepository,
)
from alphaedge.modules.market_data.infrastructure.models import BarModel, _bar_to_entity
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.infrastructure.database import async_session_factory


async def execute_backtest(run_id: UUID) -> None:
    async with async_session_factory() as session:
        run_repo = SQLAlchemyBacktestRunRepository(session)
        result_repo = SQLAlchemyBacktestResultRepository(session)
        trade_repo = SQLAlchemyBacktestTradeRepository(session)
        strategy_repo = SQLAlchemyStrategyRepository(session)
        version_repo = SQLAlchemyStrategyVersionRepository(session)

        run = await run_repo.get_by_id(run_id)
        if not run or run.status == BacktestStatus.CANCELLED:
            return

        run.status = BacktestStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await run_repo.update(run)
        await session.commit()

        try:
            version = await version_repo.get_by_id(run.strategy_version_id)
            if not version:
                raise ValueError("Strategy version not found")
            strategy = await strategy_repo.get_by_id(version.strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            config = BacktestConfig.from_dict(run.config)
            bars_by_instrument = await _load_bars(session, config)

            engine = BacktestEngine(run_id, config)
            output = engine.run(
                bars_by_instrument=bars_by_instrument,
                strategy_type=strategy.strategy_type,
                source_code=version.source_code,
                strategy_name=strategy.name,
                parameters=version.parameters,
            )

            await result_repo.save(output.result)  # type: ignore[arg-type]
            if output.trades:
                await trade_repo.save_many(output.trades)

            run.status = BacktestStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            await run_repo.update(run)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            run = await run_repo.get_by_id(run_id)
            if run:
                run.status = BacktestStatus.FAILED
                run.error_message = str(exc)[:2000]
                run.completed_at = datetime.now(UTC)
                await run_repo.update(run)
                await session.commit()
            raise


async def _load_bars(session, config: BacktestConfig) -> dict[UUID, list]:
    bars_by_instrument: dict[UUID, list] = {}
    for instrument_id in config.instrument_ids:
        stmt = (
            select(BarModel)
            .where(
                BarModel.instrument_id == instrument_id,
                BarModel.timeframe == config.timeframe,
                BarModel.timestamp >= config.start_date,
                BarModel.timestamp <= config.end_date,
            )
            .order_by(BarModel.timestamp.asc())
        )
        result = await session.execute(stmt)
        bars = [_bar_to_entity(m) for m in result.scalars().all()]
        bars_by_instrument[instrument_id] = bars
    return bars_by_instrument


def run_backtest_sync(run_id: str) -> None:
    asyncio.run(execute_backtest(UUID(run_id)))
