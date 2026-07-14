"""Interactive Brokers adapter skeleton (TWS/Gateway required for live use)."""

from decimal import Decimal
from typing import Any

from alphaedge.modules.execution.domain.broker import (
    BrokerInstrument,
    BrokerPort,
    CancelAck,
    OrderAck,
)
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.infrastructure.alpaca_broker import BrokerError


class IbkrBroker(BrokerPort):
    def __init__(self, *, account_id: str, host: str, port: int, is_paper: bool) -> None:
        self._account_id = account_id
        self._host = host
        self._port = port
        self._is_paper = is_paper

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "IbkrBroker":
        return cls(
            account_id=str(credentials.get("account_id") or ""),
            host=str(credentials.get("host") or "127.0.0.1"),
            port=int(credentials.get("port") or 7497),
            is_paper=is_paper,
        )

    async def submit_order(
        self,
        order: Order,
        instrument: BrokerInstrument,
        market_price: Decimal,
    ) -> OrderAck:
        raise BrokerError(
            "IBKR live adapter is not configured. Install TWS/IB Gateway and complete "
            "docs/BROKERS.md setup before routing orders."
        )

    async def cancel_order(self, order: Order) -> CancelAck:
        raise BrokerError("IBKR cancel is not configured on this deployment")
