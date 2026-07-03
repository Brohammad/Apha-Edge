import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyBarRepository
from alphaedge.shared.infrastructure.database import async_session_factory

ws_router = APIRouter(tags=["Market Data Streaming"])


async def _authenticate_ws(token: str | None) -> UUID | None:
    if not token:
        return None
    try:
        payload = TokenService.decode_access_token(token)
        sub = payload.get("sub")
        if sub and isinstance(sub, str):
            return UUID(sub)
    except Exception:
        return None
    return None


@ws_router.websocket("/ws/market-data")
async def market_data_stream(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    user_id = await _authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    subscriptions: set[UUID] = set()

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
            except TimeoutError:
                raw = None

            if raw:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                action = msg.get("action")
                if action == "subscribe":
                    ids = msg.get("instrument_ids") or []
                    for iid in ids:
                        subscriptions.add(UUID(str(iid)))
                    await websocket.send_json(
                        {"type": "subscribed", "instrument_ids": [str(i) for i in subscriptions]}
                    )
                elif action == "unsubscribe":
                    ids = msg.get("instrument_ids") or []
                    for iid in ids:
                        subscriptions.discard(UUID(str(iid)))
                    await websocket.send_json({"type": "unsubscribed"})
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

            if subscriptions:
                async with async_session_factory() as session:
                    bar_repo = SQLAlchemyBarRepository(session)
                    for instrument_id in list(subscriptions):
                        bar = await bar_repo.get_latest(instrument_id, Timeframe.D1)
                        if bar:
                            await websocket.send_json(
                                {
                                    "type": "bar",
                                    "instrument_id": str(instrument_id),
                                    "timeframe": bar.timeframe.value,
                                    "timestamp": bar.timestamp.isoformat(),
                                    "open": str(bar.open),
                                    "high": str(bar.high),
                                    "low": str(bar.low),
                                    "close": str(bar.close),
                                    "volume": str(bar.volume),
                                }
                            )
                await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
