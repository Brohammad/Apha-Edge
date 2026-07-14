from decimal import Decimal

from alphaedge.modules.execution.domain.broker import BrokerPort, CancelAck, FillResponse, OrderAck
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.shared.domain.value_objects import Side


class PaperBroker(BrokerPort):
    """Simulates order fills using latest market data with fixed slippage and commission."""

    def __init__(
        self,
        *,
        slippage: Decimal = Decimal("0.01"),
        commission_per_trade: Decimal = Decimal("1.0"),
        partial_fill_ratio: Decimal = Decimal("1"),
    ) -> None:
        self._slippage = slippage
        self._commission = commission_per_trade
        self._partial_fill_ratio = partial_fill_ratio

    async def submit_order(
        self,
        order: Order,
        market_price: Decimal,
        *,
        symbol: str | None = None,
    ) -> OrderAck:
        if not self._price_triggers(order, market_price):
            return OrderAck(broker_order_id=f"paper-{order.id.hex[:12]}", fill=None)

        fill_qty = (order.remaining_quantity * self._partial_fill_ratio).quantize(Decimal("0.0001"))
        if fill_qty <= 0:
            return OrderAck(broker_order_id=f"paper-{order.id.hex[:12]}", fill=None)

        fill_price = self._apply_slippage(market_price, order.side)
        fill = FillResponse(
            filled_quantity=fill_qty,
            fill_price=fill_price,
            commission=self._commission,
        )
        return OrderAck(broker_order_id=f"paper-{order.id.hex[:12]}", fill=fill)

    async def cancel_order(self, order: Order) -> CancelAck:
        return CancelAck(cancelled=True, message="Paper order cancelled")

    def _apply_slippage(self, price: Decimal, side: Side) -> Decimal:
        if side == Side.BUY:
            return price + self._slippage
        return price - self._slippage

    @staticmethod
    def _price_triggers(order: Order, market_price: Decimal) -> bool:
        if order.order_type == OrderType.MARKET:
            return True
        if order.order_type == OrderType.LIMIT:
            assert order.limit_price is not None
            if order.side == Side.BUY:
                return market_price <= order.limit_price
            return market_price >= order.limit_price
        if order.order_type == OrderType.STOP:
            assert order.stop_price is not None
            if order.side == Side.BUY:
                return market_price >= order.stop_price
            return market_price <= order.stop_price
        return False
