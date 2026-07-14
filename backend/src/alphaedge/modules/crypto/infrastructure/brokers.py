"""Binance broker adapter stub."""

from decimal import Decimal
from typing import Any

from alphaedge.modules.execution.domain.broker import BrokerInstrument, BrokerPort, CancelAck, OrderAck
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.infrastructure.alpaca_broker import BrokerError


class BinanceBroker(BrokerPort):
    def __init__(self, *, api_key: str, api_secret: str, is_paper: bool) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._is_paper = is_paper

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "BinanceBroker":
        return cls(
            api_key=str(credentials.get("api_key") or ""),
            api_secret=str(credentials.get("api_secret") or ""),
            is_paper=is_paper,
        )

    async def submit_order(self, order: Order, instrument: BrokerInstrument, market_price: Decimal) -> OrderAck:
        raise BrokerError("Binance adapter not enabled. See docs/BROKERS.md")

    async def cancel_order(self, order: Order) -> CancelAck:
        raise BrokerError("Binance cancel not configured")


class CoinbaseBroker(BrokerPort):
    def __init__(self, *, api_key: str, api_secret: str, is_paper: bool) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._is_paper = is_paper

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "CoinbaseBroker":
        return cls(
            api_key=str(credentials.get("api_key") or ""),
            api_secret=str(credentials.get("api_secret") or ""),
            is_paper=is_paper,
        )

    async def submit_order(self, order: Order, instrument: BrokerInstrument, market_price: Decimal) -> OrderAck:
        raise BrokerError("Coinbase adapter not enabled. See docs/BROKERS.md")

    async def cancel_order(self, order: Order) -> CancelAck:
        raise BrokerError("Coinbase cancel not configured")
