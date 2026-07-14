"""Exchange trading calendars for session and holiday awareness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class ExchangeCode(StrEnum):
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    NSE = "NSE"
    BSE = "BSE"


@dataclass(frozen=True)
class TradingSession:
    exchange: ExchangeCode
    open_time: time
    close_time: time
    timezone: ZoneInfo
    pre_open: time | None = None


# Indian market holidays (subset — extend via admin API in production).
_NSE_HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 26),
        date(2026, 3, 3),
        date(2026, 3, 26),
        date(2026, 4, 3),
        date(2026, 4, 14),
        date(2026, 5, 1),
        date(2026, 8, 15),
        date(2026, 10, 2),
        date(2026, 10, 20),
        date(2026, 11, 5),
        date(2026, 11, 24),
        date(2026, 12, 25),
    }
)

_US_HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
)

_SESSIONS: dict[ExchangeCode, TradingSession] = {
    ExchangeCode.NYSE: TradingSession(
        exchange=ExchangeCode.NYSE,
        open_time=time(9, 30),
        close_time=time(16, 0),
        timezone=ZoneInfo("America/New_York"),
    ),
    ExchangeCode.NASDAQ: TradingSession(
        exchange=ExchangeCode.NASDAQ,
        open_time=time(9, 30),
        close_time=time(16, 0),
        timezone=ZoneInfo("America/New_York"),
    ),
    ExchangeCode.NSE: TradingSession(
        exchange=ExchangeCode.NSE,
        open_time=time(9, 15),
        close_time=time(15, 30),
        timezone=ZoneInfo("Asia/Kolkata"),
        pre_open=time(9, 0),
    ),
    ExchangeCode.BSE: TradingSession(
        exchange=ExchangeCode.BSE,
        open_time=time(9, 15),
        close_time=time(15, 30),
        timezone=ZoneInfo("Asia/Kolkata"),
        pre_open=time(9, 0),
    ),
}


class TradingCalendar:
    """Determine whether an exchange is open at a given instant."""

    @classmethod
    def session(cls, exchange: str | ExchangeCode) -> TradingSession:
        code = ExchangeCode(exchange) if isinstance(exchange, str) else exchange
        session = _SESSIONS.get(code)
        if session is None:
            raise ValueError(f"No trading calendar for exchange: {exchange}")
        return session

    @classmethod
    def is_trading_day(cls, exchange: str | ExchangeCode, day: date) -> bool:
        if day.weekday() >= 5:
            return False
        code = ExchangeCode(exchange) if isinstance(exchange, str) else exchange
        if code in (ExchangeCode.NSE, ExchangeCode.BSE):
            return day not in _NSE_HOLIDAYS_2026
        return day not in _US_HOLIDAYS_2026

    @classmethod
    def is_market_open(cls, exchange: str | ExchangeCode, at: datetime | None = None) -> bool:
        at = at or datetime.now(UTC)
        session = cls.session(exchange)
        local = at.astimezone(session.timezone)
        if not cls.is_trading_day(session.exchange, local.date()):
            return False
        open_dt = datetime.combine(local.date(), session.open_time, tzinfo=session.timezone)
        close_dt = datetime.combine(local.date(), session.close_time, tzinfo=session.timezone)
        return open_dt <= local <= close_dt

    @classmethod
    def next_open(cls, exchange: str | ExchangeCode, after: datetime | None = None) -> datetime:
        after = after or datetime.now(UTC)
        session = cls.session(exchange)
        local = after.astimezone(session.timezone)
        candidate = local.date()
        for _ in range(10):
            if cls.is_trading_day(session.exchange, candidate):
                open_dt = datetime.combine(candidate, session.open_time, tzinfo=session.timezone)
                if open_dt > after.astimezone(session.timezone):
                    return open_dt.astimezone(UTC)
            candidate += timedelta(days=1)
        raise RuntimeError(f"Could not find next open for {exchange}")

    @classmethod
    def supported_exchanges(cls) -> list[str]:
        return [e.value for e in ExchangeCode]
