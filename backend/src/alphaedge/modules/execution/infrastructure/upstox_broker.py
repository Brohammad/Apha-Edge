"""Upstox broker adapter skeleton (OAuth 2.0)."""

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


class UpstoxBroker(BrokerPort):
    """Upstox API v2 adapter — requires OAuth access token."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        access_token: str,
        is_paper: bool,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._is_paper = is_paper

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "UpstoxBroker":
        return cls(
            api_key=str(credentials.get("api_key") or ""),
            api_secret=str(credentials.get("api_secret") or ""),
            access_token=str(credentials.get("access_token") or ""),
            is_paper=is_paper,
        )

    async def submit_order(
        self,
        order: Order,
        instrument: BrokerInstrument,
        market_price: Decimal,
    ) -> OrderAck:
        if not self._access_token:
            raise BrokerError("Upstox OAuth not completed. Store access_token after authorization.")
        raise BrokerError(
            "Upstox live order routing is not enabled. See docs/INDIAN_MARKETS.md."
        )

    async def cancel_order(self, order: Order) -> CancelAck:
        raise BrokerError("Upstox cancel is not configured on this deployment")
