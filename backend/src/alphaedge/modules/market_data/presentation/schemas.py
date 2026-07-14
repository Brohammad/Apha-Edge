from datetime import datetime

from pydantic import BaseModel, Field

from alphaedge.modules.market_data.domain.enums import AssetClass, Timeframe


class CreateInstrumentRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    exchange: str = Field(default="", max_length=20)
    asset_class: AssetClass = AssetClass.EQUITY
    currency: str = Field(default="USD", min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=255)
    metadata: dict[str, str] | None = None


class InstrumentResponse(BaseModel):
    id: str
    symbol: str
    exchange: str
    asset_class: str
    currency: str
    name: str
    is_active: bool


class BarResponse(BaseModel):
    instrument_id: str
    timeframe: str
    timestamp: datetime
    open: str
    high: str
    low: str
    close: str
    volume: str
    vwap: str | None
    source: str


class TriggerIngestionRequest(BaseModel):
    provider: str = Field(default="mock", pattern="^(mock|alpha_vantage|polygon)$")
    symbols: list[str] = Field(min_length=1)
    timeframe: Timeframe = Timeframe.D1
    start_date: datetime
    end_date: datetime


class IngestionJobResponse(BaseModel):
    id: str
    provider: str
    status: str
    symbols: list[str]
    timeframe: str
    start_date: datetime
    end_date: datetime
    records_count: int
    error_message: str | None
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None


class QuoteResponse(BaseModel):
    symbol: str
    price: str
    change_pct: str | None
    as_of: datetime
    source: str
    fallback_reason: str | None = None


class OptionContractResponse(BaseModel):
    symbol: str
    strike: str
    option_type: str
    expiry: str
    ltp: str
    oi: int
    iv: str | None = None


class OptionChainResponse(BaseModel):
    underlying: str
    spot_price: str
    as_of: datetime
    contracts: list[OptionContractResponse]
