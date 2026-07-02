from datetime import datetime

from pydantic import BaseModel, Field


class SubmitBacktestRequest(BaseModel):
    strategy_version_id: str
    name: str = Field(min_length=1, max_length=255)
    config: dict[str, object]


class BacktestRunResponse(BaseModel):
    id: str
    user_id: str
    strategy_version_id: str
    name: str
    status: str
    config: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime


class BacktestResultResponse(BaseModel):
    id: str
    backtest_run_id: str
    total_return: str
    annualized_return: str | None
    sharpe_ratio: str | None
    sortino_ratio: str | None
    max_drawdown: str
    win_rate: str | None
    total_trades: int
    profit_factor: str | None
    metrics: dict[str, object]


class BacktestTradeResponse(BaseModel):
    id: str
    instrument_id: str
    side: str
    quantity: str
    entry_price: str
    exit_price: str | None
    entry_time: datetime
    exit_time: datetime | None
    pnl: str | None
    commission: str
    slippage: str
