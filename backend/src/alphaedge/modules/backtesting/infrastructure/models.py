from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.backtesting.domain.entities import (
    BacktestResult,
    BacktestRun,
    BacktestTrade,
)
from alphaedge.modules.backtesting.domain.enums import BacktestStatus
from alphaedge.modules.backtesting.domain.repositories import (
    BacktestResultRepository,
    BacktestRunRepository,
    BacktestTradeRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BacktestRunModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "backtest_runs"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    strategy_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default=BacktestStatus.QUEUED.value, index=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(nullable=True)


class BacktestResultModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "backtest_results"

    backtest_run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False)
    total_return: Mapped[Decimal] = mapped_column(nullable=False)
    annualized_return: Mapped[Decimal | None] = mapped_column(nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(nullable=True)
    sortino_ratio: Mapped[Decimal | None] = mapped_column(nullable=True)
    max_drawdown: Mapped[Decimal] = mapped_column(nullable=False)
    win_rate: Mapped[Decimal | None] = mapped_column(nullable=True)
    total_trades: Mapped[int] = mapped_column(nullable=False)
    profit_factor: Mapped[Decimal | None] = mapped_column(nullable=True)
    equity_curve: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class BacktestTradeModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "backtest_trades"

    backtest_run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    side: Mapped[str] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(nullable=True)
    entry_time: Mapped[datetime] = mapped_column(nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(nullable=True)
    pnl: Mapped[Decimal | None] = mapped_column(nullable=True)
    commission: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    slippage: Mapped[Decimal] = mapped_column(default=Decimal("0"))


def _run_to_entity(model: BacktestRunModel) -> BacktestRun:
    return BacktestRun(
        id=model.id,
        user_id=model.user_id,
        strategy_version_id=model.strategy_version_id,
        name=model.name,
        status=BacktestStatus(model.status),
        config=model.config,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
        celery_task_id=model.celery_task_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _result_to_entity(model: BacktestResultModel) -> BacktestResult:
    return BacktestResult(
        id=model.id,
        backtest_run_id=model.backtest_run_id,
        total_return=model.total_return,
        annualized_return=model.annualized_return,
        sharpe_ratio=model.sharpe_ratio,
        sortino_ratio=model.sortino_ratio,
        max_drawdown=model.max_drawdown,
        win_rate=model.win_rate,
        total_trades=model.total_trades,
        profit_factor=model.profit_factor,
        equity_curve=model.equity_curve,
        metrics=model.metrics,
    )


def _trade_to_entity(model: BacktestTradeModel) -> BacktestTrade:
    return BacktestTrade(
        id=model.id,
        backtest_run_id=model.backtest_run_id,
        instrument_id=model.instrument_id,
        side=model.side,
        quantity=model.quantity,
        entry_price=model.entry_price,
        exit_price=model.exit_price,
        entry_time=model.entry_time,
        exit_time=model.exit_time,
        pnl=model.pnl,
        commission=model.commission,
        slippage=model.slippage,
    )


class SQLAlchemyBacktestRunRepository(BacktestRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: BacktestRun) -> BacktestRun:
        model = BacktestRunModel(
            id=run.id,
            user_id=run.user_id,
            strategy_version_id=run.strategy_version_id,
            name=run.name,
            status=run.status.value,
            config=run.config,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            celery_task_id=run.celery_task_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _run_to_entity(model)

    async def get_by_id(self, run_id: UUID) -> BacktestRun | None:
        model = await self._session.get(BacktestRunModel, run_id)
        return _run_to_entity(model) if model else None

    async def list_by_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[BacktestRun]:
        stmt = (
            select(BacktestRunModel)
            .where(BacktestRunModel.user_id == user_id)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_run_to_entity(m) for m in result.scalars().all()]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(BacktestRunModel)
            .where(BacktestRunModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update(self, run: BacktestRun) -> BacktestRun:
        model = await self._session.get(BacktestRunModel, run.id)
        if not model:
            raise ValueError(f"BacktestRun {run.id} not found")
        model.status = run.status.value
        model.started_at = run.started_at
        model.completed_at = run.completed_at
        model.error_message = run.error_message
        model.celery_task_id = run.celery_task_id
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _run_to_entity(model)


class SQLAlchemyBacktestResultRepository(BacktestResultRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, result: BacktestResult) -> BacktestResult:
        model = BacktestResultModel(
            id=result.id,
            backtest_run_id=result.backtest_run_id,
            total_return=result.total_return,
            annualized_return=result.annualized_return,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            profit_factor=result.profit_factor,
            equity_curve=result.equity_curve,
            metrics=result.metrics,
        )
        self._session.add(model)
        await self._session.flush()
        return _result_to_entity(model)

    async def get_by_run_id(self, run_id: UUID) -> BacktestResult | None:
        stmt = select(BacktestResultModel).where(BacktestResultModel.backtest_run_id == run_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _result_to_entity(model) if model else None


class SQLAlchemyBacktestTradeRepository(BacktestTradeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, trades: list[BacktestTrade]) -> None:
        for trade in trades:
            model = BacktestTradeModel(
                id=trade.id,
                backtest_run_id=trade.backtest_run_id,
                instrument_id=trade.instrument_id,
                side=trade.side,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                entry_time=trade.entry_time,
                exit_time=trade.exit_time,
                pnl=trade.pnl,
                commission=trade.commission,
                slippage=trade.slippage,
            )
            self._session.add(model)
        await self._session.flush()

    async def list_by_run_id(self, run_id: UUID) -> list[BacktestTrade]:
        stmt = (
            select(BacktestTradeModel)
            .where(BacktestTradeModel.backtest_run_id == run_id)
            .order_by(BacktestTradeModel.entry_time)
        )
        result = await self._session.execute(stmt)
        return [_trade_to_entity(m) for m in result.scalars().all()]
