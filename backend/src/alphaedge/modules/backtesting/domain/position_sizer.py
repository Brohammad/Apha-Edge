from decimal import Decimal

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.enums import PositionSizingModel
from alphaedge.modules.strategy.domain.enums import SignalAction


class PositionSizer:
    @staticmethod
    def compute_quantity(
        signal: SignalAction,
        price: Decimal,
        equity: Decimal,
        cash: Decimal,
        current_position: Decimal,
        config: BacktestConfig,
    ) -> Decimal:
        if signal == SignalAction.SELL and current_position > 0:
            return current_position

        sizing = config.position_sizing
        if sizing.model == PositionSizingModel.FIXED_QUANTITY:
            qty = sizing.value
        else:
            allocation = equity * sizing.value
            qty = (allocation / price).quantize(Decimal("0.0001")) if price > 0 else Decimal("0")

        if signal == SignalAction.BUY:
            max_affordable = (cash / price).quantize(Decimal("0.0001")) if price > 0 else Decimal("0")
            return min(qty, max_affordable)

        # Opening a short position (flat account, allow_short enforced by caller)
        return qty
