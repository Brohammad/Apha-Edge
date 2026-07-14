from enum import StrEnum


class BrokerName(StrEnum):
    PAPER = "paper"
    ALPACA = "alpaca"
    IBKR = "ibkr"
    ZERODHA = "zerodha"
    ANGELONE = "angelone"
    UPSTOX = "upstox"
    BINANCE = "binance"
    COINBASE = "coinbase"


class ProductType(StrEnum):
    """Indian broker product types (also used for margin routing)."""

    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"


class ExchangeSegment(StrEnum):
    NSE_EQ = "NSE_EQ"
    NSE_FO = "NSE_FO"
    BSE_EQ = "BSE_EQ"
    BSE_FO = "BSE_FO"


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
