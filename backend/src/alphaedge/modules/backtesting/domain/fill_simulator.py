from dataclasses import dataclass
from decimal import Decimal

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.enums import SlippageModel, TradeSide


@dataclass(frozen=True)
class FillResult:
    quantity: Decimal
    fill_price: Decimal
    commission: Decimal
    slippage_amount: Decimal


class FillSimulator:
    """Simulates order fills with slippage, commission, and partial fills."""

    @staticmethod
    def apply_slippage(
        price: Decimal, side: TradeSide, config: BacktestConfig
    ) -> tuple[Decimal, Decimal]:
        slippage = config.slippage
        if slippage.model == SlippageModel.FIXED:
            adjustment = slippage.value
        else:
            adjustment = price * slippage.value
        fill_price = price + adjustment if side == TradeSide.BUY else price - adjustment
        return fill_price, adjustment

    @classmethod
    def simulate(
        cls,
        side: TradeSide,
        requested_quantity: Decimal,
        price: Decimal,
        config: BacktestConfig,
    ) -> FillResult | None:
        if requested_quantity <= 0:
            return None
        filled_qty = (requested_quantity * config.partial_fill_ratio).quantize(Decimal("0.0001"))
        if filled_qty <= 0:
            return None
        fill_price, slippage_amt = cls.apply_slippage(price, side, config)
        commission = config.commission.per_trade
        return FillResult(
            quantity=filled_qty,
            fill_price=fill_price,
            commission=commission,
            slippage_amount=slippage_amt,
        )
