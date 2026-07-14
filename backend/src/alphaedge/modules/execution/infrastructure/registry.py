"""Broker adapter registry."""

from collections.abc import Callable

from alphaedge.modules.execution.domain.broker import BrokerPort
from alphaedge.modules.execution.domain.entities import BrokerConnection
from alphaedge.modules.execution.domain.enums import BrokerName
from alphaedge.modules.execution.domain.paper_broker import PaperBroker
from alphaedge.modules.execution.infrastructure.alpaca_broker import AlpacaBroker
from alphaedge.modules.execution.infrastructure.ibkr_broker import IbkrBroker

BrokerFactory = Callable[[BrokerConnection], BrokerPort]

_REGISTRY: dict[BrokerName, BrokerFactory] = {
    BrokerName.PAPER: lambda _c: PaperBroker(),
    BrokerName.ALPACA: lambda c: AlpacaBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.IBKR: lambda c: IbkrBroker.from_credentials(c.credentials, c.is_paper),
}


def get_broker(connection: BrokerConnection) -> BrokerPort:
    factory = _REGISTRY.get(connection.broker_name)
    if factory is None:
        raise ValueError(f"Unsupported broker: {connection.broker_name.value}")
    return factory(connection)


def register_broker(broker_name: BrokerName, factory: BrokerFactory) -> None:
    _REGISTRY[broker_name] = factory
