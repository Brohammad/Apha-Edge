from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.modules.execution.infrastructure.alpaca_broker import AlpacaBroker
from alphaedge.shared.domain.value_objects import Side


def _market_order() -> Order:
    return Order.create(
        portfolio_id=uuid4(),
        broker_connection_id=uuid4(),
        instrument_id=uuid4(),
        side=Side.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10"),
    )


@pytest.mark.asyncio
async def test_alpaca_broker_simulates_without_credentials():
    broker = AlpacaBroker(api_key="", api_secret="", base_url="https://paper-api.alpaca.markets")
    order = _market_order()
    ack = await broker.submit_order(order, Decimal("100"))
    assert ack.broker_order_id.startswith("alpaca-sim-paper-")
    assert ack.fill is not None
    assert ack.fill.filled_quantity > 0
