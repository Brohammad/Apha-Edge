from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass(frozen=True)
class RawBar:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None


class BarValidator:
    @staticmethod
    def validate(raw: RawBar) -> RawBar:
        if raw.high < raw.low:
            raise ValidationError(f"Invalid OHLC for {raw.symbol}: high < low")
        if raw.open < 0 or raw.close < 0 or raw.high < 0 or raw.low < 0:
            raise ValidationError(f"Negative price for {raw.symbol}")
        if raw.volume < 0:
            raise ValidationError(f"Negative volume for {raw.symbol}")
        if raw.timestamp.tzinfo is None:
            raise ValidationError(f"Timestamp must be timezone-aware for {raw.symbol}")
        return raw


class BarNormalizer:
    @staticmethod
    def to_domain(
        raw: RawBar,
        instrument_id: object,
        timeframe: Timeframe,
        source: str,
    ) -> Bar:
        from uuid import UUID

        validated = BarValidator.validate(raw)
        return Bar(
            instrument_id=UUID(str(instrument_id)),
            timeframe=timeframe,
            timestamp=validated.timestamp,
            open=validated.open,
            high=validated.high,
            low=validated.low,
            close=validated.close,
            volume=validated.volume,
            vwap=validated.vwap,
            source=source,
        )
