from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alphaedge.modules.backtesting.domain.entities import (
    BacktestResult,
    BacktestRun,
    BacktestTrade,
)


@dataclass(frozen=True)
class SubmitBacktestCommand:
    user_id: UUID
    strategy_version_id: UUID
    name: str
    config: dict[str, object]


@dataclass(frozen=True)
class ListBacktestRunsQuery:
    user_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetBacktestRunQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class GetBacktestResultQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class GetBacktestTradesQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class GetEquityCurveQuery:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class DeleteBacktestRunCommand:
    user_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class BacktestRunDTO:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    name: str
    status: str
    config: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_entity(entity: BacktestRun) -> "BacktestRunDTO":
        return BacktestRunDTO(
            id=entity.id,
            user_id=entity.user_id,
            strategy_version_id=entity.strategy_version_id,
            name=entity.name,
            status=entity.status.value,
            config=entity.config,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            error_message=entity.error_message,
            celery_task_id=entity.celery_task_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@dataclass(frozen=True)
class BacktestResultDTO:
    id: UUID
    backtest_run_id: UUID
    total_return: str
    annualized_return: str | None
    sharpe_ratio: str | None
    sortino_ratio: str | None
    max_drawdown: str
    win_rate: str | None
    total_trades: int
    profit_factor: str | None
    equity_curve: list[dict[str, object]]
    metrics: dict[str, object]

    @staticmethod
    def from_entity(entity: BacktestResult) -> "BacktestResultDTO":
        return BacktestResultDTO(
            id=entity.id,
            backtest_run_id=entity.backtest_run_id,
            total_return=str(entity.total_return),
            annualized_return=str(entity.annualized_return)
            if entity.annualized_return is not None
            else None,
            sharpe_ratio=str(entity.sharpe_ratio) if entity.sharpe_ratio is not None else None,
            sortino_ratio=str(entity.sortino_ratio) if entity.sortino_ratio is not None else None,
            max_drawdown=str(entity.max_drawdown),
            win_rate=str(entity.win_rate) if entity.win_rate is not None else None,
            total_trades=entity.total_trades,
            profit_factor=str(entity.profit_factor) if entity.profit_factor is not None else None,
            equity_curve=entity.equity_curve,
            metrics=entity.metrics,
        )


@dataclass(frozen=True)
class BacktestTradeDTO:
    id: UUID
    backtest_run_id: UUID
    instrument_id: UUID
    side: str
    quantity: str
    entry_price: str
    exit_price: str | None
    entry_time: datetime
    exit_time: datetime | None
    pnl: str | None
    commission: str
    slippage: str

    @staticmethod
    def from_entity(entity: BacktestTrade) -> "BacktestTradeDTO":
        return BacktestTradeDTO(
            id=entity.id,
            backtest_run_id=entity.backtest_run_id,
            instrument_id=entity.instrument_id,
            side=entity.side,
            quantity=str(entity.quantity),
            entry_price=str(entity.entry_price),
            exit_price=str(entity.exit_price) if entity.exit_price is not None else None,
            entry_time=entity.entry_time,
            exit_time=entity.exit_time,
            pnl=str(entity.pnl) if entity.pnl is not None else None,
            commission=str(entity.commission),
            slippage=str(entity.slippage),
        )
