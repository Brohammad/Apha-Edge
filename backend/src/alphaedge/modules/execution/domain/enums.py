from enum import StrEnum


class BrokerName(StrEnum):
    PAPER = "paper"
    ALPACA = "alpaca"
    IBKR = "ibkr"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderEventType(StrEnum):
    CREATED = "created"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RETRY = "retry"
