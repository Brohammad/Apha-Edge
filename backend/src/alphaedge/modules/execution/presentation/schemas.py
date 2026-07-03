from datetime import datetime

from pydantic import BaseModel, Field


class CreateBrokerConnectionRequest(BaseModel):
    broker_name: str = Field(default="paper")
    credentials: dict[str, object] | None = None
    is_paper: bool = True


class BrokerConnectionResponse(BaseModel):
    id: str
    user_id: str
    broker_name: str
    is_paper: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubmitOrderRequest(BaseModel):
    portfolio_id: str
    broker_connection_id: str
    instrument_id: str
    side: str
    order_type: str = Field(default="market")
    quantity: str
    limit_price: str | None = None
    stop_price: str | None = None
    idempotency_key: str | None = None
    live_trading_acknowledged: bool = False


class OrderResponse(BaseModel):
    id: str
    portfolio_id: str
    broker_connection_id: str
    instrument_id: str
    side: str
    order_type: str
    quantity: str
    filled_quantity: str
    limit_price: str | None
    stop_price: str | None
    status: str
    broker_order_id: str | None
    idempotency_key: str | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ExecutionResponse(BaseModel):
    id: str
    order_id: str
    quantity: str
    price: str
    commission: str
    executed_at: datetime
