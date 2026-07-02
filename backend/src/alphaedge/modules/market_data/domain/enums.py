from enum import StrEnum


class AssetClass(StrEnum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
