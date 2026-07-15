"""Broker registry implementation gating."""

from alphaedge.modules.execution.domain.enums import BrokerName
from alphaedge.modules.execution.infrastructure.registry import (
    is_broker_implemented,
    list_implemented_brokers,
)


def test_only_paper_and_alpaca_are_implemented() -> None:
    assert is_broker_implemented(BrokerName.PAPER)
    assert is_broker_implemented(BrokerName.ALPACA)
    assert not is_broker_implemented(BrokerName.IBKR)
    assert not is_broker_implemented(BrokerName.ZERODHA)
    assert not is_broker_implemented(BrokerName.BINANCE)
    assert list_implemented_brokers() == ["alpaca", "paper"]
