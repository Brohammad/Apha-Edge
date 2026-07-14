"""Zerodha Kite Connect broker adapter (OAuth + order routing skeleton)."""

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


class ZerodhaBroker(BrokerPort):
  """Kite Connect adapter — requires OAuth access token and API key."""

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
  def from_credentials(cls, credentials: dict[str, Any], is_paper: bool) -> "ZerodhaBroker":
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
          raise BrokerError(
              "Zerodha OAuth not completed. Connect via Kite Connect and store access_token."
          )
      raise BrokerError(
          "Zerodha live order routing is not enabled on this deployment. "
          "See docs/INDIAN_MARKETS.md for setup."
      )

  async def cancel_order(self, order: Order) -> CancelAck:
      raise BrokerError("Zerodha cancel is not configured on this deployment")
