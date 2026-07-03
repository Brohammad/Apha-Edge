"""WebSocket authentication via short-lived tickets."""

from __future__ import annotations

from uuid import UUID

from fastapi import WebSocket

from alphaedge.config import settings
from alphaedge.modules.identity.application.services import TokenService
from alphaedge.shared.infrastructure.ws_tickets import consume_ws_ticket


async def authenticate_websocket(websocket: WebSocket) -> UUID | None:
    protocol = websocket.headers.get("sec-websocket-protocol", "")
    if protocol.startswith("ticket."):
        return await consume_ws_ticket(protocol[len("ticket.") :])

    if not settings.is_production:
        token = websocket.query_params.get("token")
        if token:
            try:
                payload = TokenService.decode_access_token(token)
                sub = payload.get("sub")
                if sub and isinstance(sub, str):
                    return UUID(sub)
            except Exception:
                return None
    return None
