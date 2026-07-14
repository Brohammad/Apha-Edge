"""Crypto asset class and 24/7 trading calendar."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo


class CryptoExchange(StrEnum):
    BINANCE = "binance"
    COINBASE = "coinbase"


class CryptoTradingCalendar:
    @staticmethod
    def is_market_open(_exchange: str | CryptoExchange, at: datetime | None = None) -> bool:
        return True  # 24/7

    @staticmethod
    def session_timezone() -> ZoneInfo:
        return ZoneInfo("UTC")

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)
