"""Alpaca Markets REST adapter."""

from decimal import Decimal
from typing import Any

import httpx

from alphaedge.config import settings
from alphaedge.modules.execution.domain.broker import BrokerPort, CancelAck, FillResponse, OrderAck
from alphaedge.modules.execution.domain.entities import Order
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.modules.execution.domain.paper_broker import PaperBroker


class BrokerError(Exception):
    """Raised when a live broker API call fails."""


class AlpacaBroker(BrokerPort):
    """Alpaca Markets REST adapter. Paper mode may simulate when credentials are absent."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str,
        is_paper: bool = True,
        paper_fallback: PaperBroker | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._is_paper = is_paper
        self._fallback = paper_fallback or PaperBroker()

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "AlpacaBroker":
        api_key = str(credentials.get("api_key") or "")
        api_secret = str(credentials.get("api_secret") or "")
        if not api_key or not api_secret:
            if not is_paper:
                raise BrokerError("Live Alpaca orders require per-connection API credentials")
            api_key = str(credentials.get("api_key") or settings.alpaca_api_key)
            api_secret = str(credentials.get("api_secret") or settings.alpaca_api_secret)
        base_url = str(
            credentials.get("base_url")
            or (settings.alpaca_paper_base_url if is_paper else settings.alpaca_live_base_url)
        )
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            is_paper=is_paper,
        )

    def _has_credentials(self) -> bool:
        return bool(self._api_key and self._api_secret)

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
            "Content-Type": "application/json",
        }

    async def submit_order(self, order: Order, market_price: Decimal) -> OrderAck:
        if not self._has_credentials():
            if not self._is_paper:
                raise BrokerError("Missing Alpaca credentials for live trading")
            ack = await self._fallback.submit_order(order, market_price)
            return OrderAck(
                broker_order_id=f"alpaca-sim-{ack.broker_order_id}",
                fill=ack.fill,
            )

        payload = {
            "symbol": str(order.instrument_id)[:8],
            "qty": str(order.remaining_quantity),
            "side": order.side.value,
            "type": order.order_type.value,
            "time_in_force": "day",
        }
        if order.order_type == OrderType.LIMIT and order.limit_price is not None:
            payload["limit_price"] = str(order.limit_price)
        if order.order_type == OrderType.STOP and order.stop_price is not None:
            payload["stop_price"] = str(order.stop_price)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code >= 400:
                raise BrokerError(
                    f"Alpaca order rejected (HTTP {resp.status_code}): {resp.text[:200]}"
                )
            data = resp.json()

        broker_id = str(data.get("id", order.id))
        filled_qty = Decimal(str(data.get("filled_qty") or "0"))
        if filled_qty <= 0:
            return OrderAck(broker_order_id=broker_id, fill=None)

        fill_price = Decimal(str(data.get("filled_avg_price") or market_price))
        fill = FillResponse(
            filled_quantity=filled_qty,
            fill_price=fill_price,
            commission=Decimal("0"),
        )
        return OrderAck(broker_order_id=broker_id, fill=fill)

    async def cancel_order(self, order: Order) -> CancelAck:
        if not self._has_credentials() or not order.broker_order_id:
            if not self._is_paper:
                raise BrokerError("Missing Alpaca credentials for live cancel")
            return await self._fallback.cancel_order(order)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{self._base_url}/v2/orders/{order.broker_order_id}",
                headers=self._headers(),
            )
        if resp.status_code in (200, 204):
            return CancelAck(cancelled=True)
        if resp.status_code >= 400:
            raise BrokerError(f"Alpaca cancel failed (HTTP {resp.status_code})")
        return CancelAck(cancelled=False, message=resp.text[:200])
