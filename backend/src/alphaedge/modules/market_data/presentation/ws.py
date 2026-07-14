import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from alphaedge.modules.market_data.infrastructure.bar_pubsub import bar_channel
from alphaedge.shared.infrastructure.metrics import WS_CONNECTIONS, WS_MESSAGES
from alphaedge.shared.infrastructure.pubsub import subscribe_channel
from alphaedge.shared.presentation.ws_auth import authenticate_websocket

ws_router = APIRouter(tags=["Market Data Streaming"])

_CHANNEL = "market_data"


@ws_router.websocket("/ws/market-data")
async def market_data_stream(websocket: WebSocket):
    user_id = await authenticate_websocket(websocket)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept(subprotocol=websocket.headers.get("sec-websocket-protocol"))
    WS_CONNECTIONS.labels(channel=_CHANNEL).inc()
    subscriptions: set[UUID] = set()
    forward_tasks: dict[UUID, asyncio.Task] = {}

    async def forward_bar(instrument_id: UUID) -> None:
        channel = bar_channel(instrument_id)
        try:
            async for payload in subscribe_channel(channel):
                if payload.get("type") == "heartbeat":
                    continue
                await websocket.send_json(payload)
                WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()
        except asyncio.CancelledError:
            raise

    def subscribe_instrument(instrument_id: UUID) -> None:
        if instrument_id in subscriptions:
            return
        subscriptions.add(instrument_id)
        forward_tasks[instrument_id] = asyncio.create_task(forward_bar(instrument_id))

    def unsubscribe_instrument(instrument_id: UUID) -> None:
        subscriptions.discard(instrument_id)
        task = forward_tasks.pop(instrument_id, None)
        if task:
            task.cancel()

    try:
        while True:
            raw = await websocket.receive_text()
            WS_MESSAGES.labels(channel=_CHANNEL, direction="in").inc()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()
                continue

            action = msg.get("action")
            if action == "subscribe":
                ids = msg.get("instrument_ids") or []
                for iid in ids:
                    subscribe_instrument(UUID(str(iid)))
                await websocket.send_json(
                    {"type": "subscribed", "instrument_ids": [str(i) for i in subscriptions]}
                )
                WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()
            elif action == "unsubscribe":
                ids = msg.get("instrument_ids") or []
                for iid in ids:
                    unsubscribe_instrument(UUID(str(iid)))
                await websocket.send_json({"type": "unsubscribed"})
                WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
                WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()
    except WebSocketDisconnect:
        return
    finally:
        for task in forward_tasks.values():
            task.cancel()
        if forward_tasks:
            await asyncio.gather(*forward_tasks.values(), return_exceptions=True)
        WS_CONNECTIONS.labels(channel=_CHANNEL).dec()
