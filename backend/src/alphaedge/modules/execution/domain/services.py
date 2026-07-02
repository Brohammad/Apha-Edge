from datetime import UTC, datetime
from decimal import Decimal

from alphaedge.modules.execution.domain.entities import Execution, Order, OrderEvent
from alphaedge.modules.execution.domain.enums import OrderEventType
from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.domain.value_objects import Side


class PortfolioUpdater:
    """Apply execution fills to portfolio cash and holdings."""

    @staticmethod
    def apply_fill(
        portfolio: Portfolio,
        holding: Holding | None,
        *,
        instrument_id,
        side: Side,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
    ) -> Holding | None:
        notional = quantity * price
        if side == Side.BUY:
            total_cost = notional + commission
            if portfolio.cash_balance < total_cost:
                raise ValidationError("Insufficient cash for buy order")
            portfolio.cash_balance -= total_cost
            if holding is None:
                return Holding.create(
                    portfolio_id=portfolio.id,
                    instrument_id=instrument_id,
                    quantity=quantity,
                    avg_cost=price,
                    current_price=price,
                )
            new_qty = holding.quantity + quantity
            holding.avg_cost = (
                (holding.quantity * holding.avg_cost) + (quantity * price)
            ) / new_qty
            holding.quantity = new_qty
            holding.refresh_price(price)
            return holding

        if holding is None or holding.quantity < quantity:
            raise ValidationError("Insufficient holdings for sell order")
        proceeds = notional - commission
        portfolio.cash_balance += proceeds
        holding.quantity -= quantity
        holding.refresh_price(price)
        return holding


def record_event(
    order: Order,
    event_type: OrderEventType,
    payload: dict[str, object] | None = None,
) -> OrderEvent:
    return OrderEvent.create(order.id, event_type, payload)


def record_execution(
    order: Order,
    quantity: Decimal,
    price: Decimal,
    commission: Decimal,
) -> Execution:
    return Execution.create(
        order_id=order.id,
        quantity=quantity,
        price=price,
        commission=commission,
        executed_at=datetime.now(UTC),
    )
