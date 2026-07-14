from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.modules.execution.domain.broker import BrokerInstrument
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.modules.execution.domain.paper_broker import PaperBroker
from alphaedge.modules.execution.domain.services import PortfolioUpdater
from alphaedge.modules.portfolio.domain.entities import Portfolio
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.domain.value_objects import Side

_INST = BrokerInstrument(symbol="AAPL", exchange="NASDAQ", currency="USD", metadata={})


@pytest.mark.asyncio
async def test_paper_broker_market_buy_fill():
    broker = PaperBroker(slippage=Decimal("0.01"), commission_per_trade=Decimal("1"))
    order = Order.create(
        portfolio_id=uuid4(),
        broker_connection_id=uuid4(),
        instrument_id=uuid4(),
        side=Side.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10"),
    )
    ack = await broker.submit_order(order, _INST, Decimal("100"))
    assert ack.fill is not None
    assert ack.fill.filled_quantity == Decimal("10")
    assert ack.fill.fill_price == Decimal("100.01")
    assert ack.fill.commission == Decimal("1")


@pytest.mark.asyncio
async def test_paper_broker_limit_buy_not_triggered():
    broker = PaperBroker()
    order = Order.create(
        portfolio_id=uuid4(),
        broker_connection_id=uuid4(),
        instrument_id=uuid4(),
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("5"),
        limit_price=Decimal("90"),
    )
    ack = await broker.submit_order(order, _INST, Decimal("100"))
    assert ack.fill is None


@pytest.mark.asyncio
async def test_paper_broker_limit_buy_triggered():
    broker = PaperBroker(slippage=Decimal("0"))
    order = Order.create(
        portfolio_id=uuid4(),
        broker_connection_id=uuid4(),
        instrument_id=uuid4(),
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("5"),
        limit_price=Decimal("100"),
    )
    ack = await broker.submit_order(order, _INST, Decimal("99"))
    assert ack.fill is not None
    assert ack.fill.fill_price == Decimal("99")


def test_portfolio_updater_buy_and_sell():
    portfolio = Portfolio.create(uuid4(), "Test", Decimal("10000"))
    instrument_id = uuid4()
    holding = PortfolioUpdater.apply_fill(
        portfolio,
        None,
        instrument_id=instrument_id,
        side=Side.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("1"),
    )
    assert holding is not None
    assert holding.quantity == Decimal("10")
    assert portfolio.cash_balance == Decimal("8999")

    PortfolioUpdater.apply_fill(
        portfolio,
        holding,
        instrument_id=instrument_id,
        side=Side.SELL,
        quantity=Decimal("10"),
        price=Decimal("110"),
        commission=Decimal("1"),
    )
    assert holding.quantity == Decimal("0")
    assert portfolio.cash_balance == Decimal("10098")


def test_portfolio_updater_insufficient_cash():
    portfolio = Portfolio.create(uuid4(), "Test", Decimal("100"))
    with pytest.raises(ValidationError):
        PortfolioUpdater.apply_fill(
            portfolio,
            None,
            instrument_id=uuid4(),
            side=Side.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            commission=Decimal("0"),
        )


def test_order_cancel_and_fill():
    order = Order.create(
        portfolio_id=uuid4(),
        broker_connection_id=uuid4(),
        instrument_id=uuid4(),
        side=Side.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10"),
    )
    assert order.can_cancel()
    order.apply_fill(Decimal("10"))
    assert order.status.value == "filled"
    assert not order.can_cancel()
