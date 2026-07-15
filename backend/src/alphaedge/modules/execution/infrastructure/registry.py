"""Broker adapter registry.

Only Paper and Alpaca are production-ready for order submission. Stub adapters
remain registered for development/tests via ``register_broker``, but
``is_broker_implemented`` gates user-facing connection creation.
"""

from collections.abc import Callable

from alphaedge.modules.crypto.infrastructure.brokers import BinanceBroker, CoinbaseBroker
from alphaedge.modules.execution.domain.broker import BrokerPort
from alphaedge.modules.execution.domain.entities import BrokerConnection
from alphaedge.modules.execution.domain.enums import BrokerName
from alphaedge.modules.execution.domain.paper_broker import PaperBroker
from alphaedge.modules.execution.infrastructure.alpaca_broker import AlpacaBroker
from alphaedge.modules.execution.infrastructure.angelone_broker import AngelOneBroker
from alphaedge.modules.execution.infrastructure.ibkr_broker import IbkrBroker
from alphaedge.modules.execution.infrastructure.upstox_broker import UpstoxBroker
from alphaedge.modules.execution.infrastructure.zerodha_broker import ZerodhaBroker

BrokerFactory = Callable[[BrokerConnection], BrokerPort]

# Brokers that can actually submit orders end-to-end today.
IMPLEMENTED_BROKERS: frozenset[BrokerName] = frozenset(
    {BrokerName.PAPER, BrokerName.ALPACA}
)

_REGISTRY: dict[BrokerName, BrokerFactory] = {
    BrokerName.PAPER: lambda _c: PaperBroker(),
    BrokerName.ALPACA: lambda c: AlpacaBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.IBKR: lambda c: IbkrBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.ZERODHA: lambda c: ZerodhaBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.ANGELONE: lambda c: AngelOneBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.UPSTOX: lambda c: UpstoxBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.BINANCE: lambda c: BinanceBroker.from_credentials(c.credentials, c.is_paper),
    BrokerName.COINBASE: lambda c: CoinbaseBroker.from_credentials(c.credentials, c.is_paper),
}


def is_broker_implemented(broker_name: BrokerName) -> bool:
    return broker_name in IMPLEMENTED_BROKERS


def list_implemented_brokers() -> list[str]:
    return sorted(b.value for b in IMPLEMENTED_BROKERS)


def get_broker(connection: BrokerConnection) -> BrokerPort:
    factory = _REGISTRY.get(connection.broker_name)
    if factory is None:
        raise ValueError(f"Unsupported broker: {connection.broker_name.value}")
    return factory(connection)


def register_broker(broker_name: BrokerName, factory: BrokerFactory) -> None:
    _REGISTRY[broker_name] = factory
