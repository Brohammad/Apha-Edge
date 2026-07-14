import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from alphaedge.modules.execution.infrastructure.order_pubsub import order_channel
from alphaedge.shared.infrastructure.metrics import WS_CONNECTIONS, WS_MESSAGES
from alphaedge.shared.infrastructure.pubsub import subscribe_channel
from alphaedge.shared.presentation.ws_auth import authenticate_websocket

order_ws_router = APIRouter(tags=["Execution Streaming"])

_CHANNEL = "orders"


@order_ws_router.websocket("/ws/orders")
async def order_updates_stream(websocket: WebSocket):
    user_id = await authenticate_websocket(websocket)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept(subprotocol=websocket.headers.get("sec-websocket-protocol"))
    WS_CONNECTIONS.labels(channel=_CHANNEL).inc()
    channel = order_channel(user_id)

    async def forward_events() -> None:
        async for payload in subscribe_channel(channel):
            if payload.get("type") == "heartbeat":
                continue
            await websocket.send_json(payload)
            WS_MESSAGES.labels(channel=_CHANNEL, direction="out").inc()

    forward_task = asyncio.create_task(forward_events())

    try:
        while True:
            raw = await websocket.receive_text()
            WS_MESSAGES.labels(channel=_CHANNEL, direction="in").inc()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue
            if msg.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        WS_CONNECTIONS.labels(channel=_CHANNEL).dec()
