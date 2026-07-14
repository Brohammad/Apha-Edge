"""Angel One SmartAPI broker adapter skeleton."""

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


class AngelOneBroker(BrokerPort):
    """Angel One SmartAPI adapter — requires API key, client code, and TOTP."""

    def __init__(
        self,
        *,
        api_key: str,
        client_code: str,
        password: str,
        totp_secret: str,
        is_paper: bool,
    ) -> None:
        self._api_key = api_key
        self._client_code = client_code
        self._password = password
        self._totp_secret = totp_secret
        self._is_paper = is_paper

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "AngelOneBroker":
        return cls(
            api_key=str(credentials.get("api_key") or ""),
            client_code=str(credentials.get("client_code") or ""),
            password=str(credentials.get("password") or ""),
            totp_secret=str(credentials.get("totp_secret") or ""),
            is_paper=is_paper,
        )

    async def submit_order(
        self,
        order: Order,
        instrument: BrokerInstrument,
        market_price: Decimal,
    ) -> OrderAck:
        if not self._api_key or not self._client_code:
            raise BrokerError("Angel One credentials incomplete (api_key, client_code required)")
        raise BrokerError(
            "Angel One live order routing is not enabled. See docs/INDIAN_MARKETS.md."
        )

    async def cancel_order(self, order: Order) -> CancelAck:
        raise BrokerError("Angel One cancel is not configured on this deployment")
