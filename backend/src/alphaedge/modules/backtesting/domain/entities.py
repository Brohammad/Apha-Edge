from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.backtesting.domain.enums import BacktestStatus
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class BacktestRun:
    id: UUID
    user_id: UUID
    strategy_version_id: UUID
    name: str
    status: BacktestStatus
    config: dict[str, object]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        user_id: UUID,
        strategy_version_id: UUID,
        name: str,
        config: dict[str, object],
    ) -> "BacktestRun":
        name = name.strip()
        if not name:
            raise ValidationError("Backtest name is required")
        return BacktestRun(
            id=uuid4(),
            user_id=user_id,
            strategy_version_id=strategy_version_id,
            name=name,
            status=BacktestStatus.QUEUED,
            config=config,
        )


@dataclass
class BacktestResult:
    id: UUID
    backtest_run_id: UUID
    total_return: Decimal
    annualized_return: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    max_drawdown: Decimal
    win_rate: Decimal | None
    total_trades: int
    profit_factor: Decimal | None
    equity_curve: list[dict[str, object]]
    metrics: dict[str, object]

    @staticmethod
    def create(
        backtest_run_id: UUID,
        total_return: Decimal,
        max_drawdown: Decimal,
        total_trades: int,
        equity_curve: list[dict[str, object]],
        metrics: dict[str, object],
        *,
        annualized_return: Decimal | None = None,
        sharpe_ratio: Decimal | None = None,
        sortino_ratio: Decimal | None = None,
        win_rate: Decimal | None = None,
        profit_factor: Decimal | None = None,
    ) -> "BacktestResult":
        return BacktestResult(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_factor=profit_factor,
            equity_curve=equity_curve,
            metrics=metrics,
        )


@dataclass
class BacktestTrade:
    id: UUID
    backtest_run_id: UUID
    instrument_id: UUID
    side: str
    quantity: Decimal
    entry_price: Decimal
    entry_time: datetime
    exit_price: Decimal | None = None
    exit_time: datetime | None = None
    pnl: Decimal | None = None
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")

    @staticmethod
    def open(
        backtest_run_id: UUID,
        instrument_id: UUID,
        quantity: Decimal,
        entry_price: Decimal,
        entry_time: datetime,
        commission: Decimal,
        slippage: Decimal,
        *,
        side: str = "buy",
    ) -> "BacktestTrade":
        if side not in ("buy", "sell"):
            raise ValidationError(f"Invalid trade side: {side}")
        return BacktestTrade(
            id=uuid4(),
            backtest_run_id=backtest_run_id,
            instrument_id=instrument_id,
            side=side,
            quantity=abs(quantity),
            entry_price=entry_price,
            entry_time=entry_time,
            commission=commission,
            slippage=slippage,
        )

    def close(
        self,
        exit_price: Decimal,
        exit_time: datetime,
        extra_commission: Decimal,
        extra_slippage: Decimal,
    ) -> None:
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.commission += extra_commission
        self.slippage += extra_slippage
        if self.side == "buy":
            gross = (exit_price - self.entry_price) * self.quantity
        else:
            gross = (self.entry_price - exit_price) * self.quantity
        self.pnl = gross - self.commission
