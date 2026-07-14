"""Redis Pub/Sub helpers for real-time event fan-out."""

import json
from collections.abc import AsyncIterator
from typing import Any

from alphaedge.shared.infrastructure.redis import get_redis


async def publish_event(channel: str, payload: dict[str, Any]) -> None:
    redis = await get_redis()
    await redis.publish(channel, json.dumps(payload))


async def subscribe_channel(channel: str) -> AsyncIterator[dict[str, Any]]:
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is None:
                yield {"type": "heartbeat"}
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode()
            if isinstance(data, str):
                yield json.loads(data)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
