from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.market_data.domain.enums import AssetClass, IngestionStatus, Timeframe
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class Instrument:
    id: UUID
    symbol: str
    exchange: str
    asset_class: AssetClass
    currency: str
    name: str
    is_active: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def create(
        symbol: str,
        exchange: str,
        asset_class: AssetClass,
        currency: str,
        name: str,
        metadata: dict[str, str] | None = None,
    ) -> "Instrument":
        symbol = symbol.upper().strip()
        if not symbol:
            raise ValidationError("Symbol is required")
        return Instrument(
            id=uuid4(),
            symbol=symbol,
            exchange=exchange.strip(),
            asset_class=asset_class,
            currency=currency.upper(),
            name=name.strip(),
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class Bar:
    instrument_id: UUID
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None
    source: str = "mock"

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValidationError("Bar high cannot be less than low")
        if self.open < 0 or self.close < 0:
            raise ValidationError("Bar prices cannot be negative")


@dataclass
class IngestionJob:
    id: UUID
    provider: str
    status: IngestionStatus
    symbols: list[str]
    timeframe: Timeframe
    start_date: datetime
    end_date: datetime
    records_count: int = 0
    error_message: str | None = None
    celery_task_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        provider: str,
        symbols: list[str],
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
    ) -> "IngestionJob":
        if not symbols:
            raise ValidationError("At least one symbol is required")
        if start_date >= end_date:
            raise ValidationError("start_date must be before end_date")
        return IngestionJob(
            id=uuid4(),
            provider=provider,
            status=IngestionStatus.PENDING,
            symbols=[s.upper() for s in symbols],
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )
