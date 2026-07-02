from enum import StrEnum


class BacktestStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SlippageModel(StrEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class PositionSizingModel(StrEnum):
    FIXED_QUANTITY = "fixed_quantity"
    PERCENT_EQUITY = "percent_equity"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
