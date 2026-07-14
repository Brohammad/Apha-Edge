from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from alphaedge.modules.execution.domain.broker import BrokerInstrument
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.modules.execution.infrastructure.alpaca_broker import AlpacaBroker, BrokerError
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


def _instrument() -> BrokerInstrument:
    return BrokerInstrument(symbol="AAPL", exchange="NASDAQ", currency="USD", metadata={})


@pytest.mark.asyncio
async def test_alpaca_broker_simulates_without_credentials():
    broker = AlpacaBroker(api_key="", api_secret="", base_url="https://paper-api.alpaca.markets")
    order = _market_order()
    ack = await broker.submit_order(order, _instrument(), Decimal("100"))
    assert ack.broker_order_id.startswith("alpaca-sim-paper-")
    assert ack.fill is not None
    assert ack.fill.filled_quantity > 0


@pytest.mark.asyncio
async def test_alpaca_broker_requires_symbol_with_credentials():
    broker = AlpacaBroker(
        api_key="key",
        api_secret="secret",
        base_url="https://paper-api.alpaca.markets",
    )
    order = _market_order()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "broker-123",
        "filled_qty": "10",
        "filled_avg_price": "150.25",
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "alphaedge.modules.execution.infrastructure.alpaca_broker.httpx.AsyncClient",
        return_value=mock_client,
    ):
        ack = await broker.submit_order(order, _instrument(), Decimal("150"))

    assert ack.broker_order_id == "broker-123"
    assert ack.fill is not None
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["json"]["symbol"] == "AAPL"
