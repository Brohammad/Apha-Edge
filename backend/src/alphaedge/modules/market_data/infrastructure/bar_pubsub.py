"""Publish bar updates to Redis for WebSocket subscribers."""

from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.shared.infrastructure.pubsub import publish_event


def bar_channel(instrument_id: UUID) -> str:
    return f"bars:instrument:{instrument_id}"


async def publish_bar_update(bar: Bar) -> None:
    await publish_event(
        bar_channel(bar.instrument_id),
        {
            "type": "bar",
            "instrument_id": str(bar.instrument_id),
            "timeframe": bar.timeframe.value,
            "timestamp": bar.timestamp.isoformat(),
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": str(bar.volume),
        },
    )
