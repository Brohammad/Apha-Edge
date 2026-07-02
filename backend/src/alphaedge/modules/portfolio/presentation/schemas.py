from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    initial_capital: Decimal = Field(gt=0)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    is_paper: bool = True


class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    name: str
    base_currency: str
    initial_capital: str
    cash_balance: str
    is_paper: bool
    created_at: datetime
    updated_at: datetime


class HoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    instrument_id: str
    quantity: str
    avg_cost: str
    current_price: str
    market_value: str
    updated_at: datetime


class RebalanceRequest(BaseModel):
    target_allocation: dict[str, float]


class RebalancePlanResponse(BaseModel):
    id: str
    portfolio_id: str
    target_allocation: dict[str, float]
    proposed_trades: list[dict[str, object]]
    status: str
    created_at: datetime


class SyncFromBacktestRequest(BaseModel):
    backtest_run_id: str
