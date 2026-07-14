"""Publish order status updates to Redis for WebSocket subscribers."""

from uuid import UUID

from alphaedge.shared.infrastructure.pubsub import publish_event


def order_channel(user_id: UUID) -> str:
    return f"orders:user:{user_id}"


async def publish_order_update(
    *,
    user_id: UUID,
    order_id: UUID,
    portfolio_id: UUID,
    status: str,
    filled_quantity: str,
    event_type: str,
) -> None:
    await publish_event(
        order_channel(user_id),
        {
            "type": "order_update",
            "order_id": str(order_id),
            "portfolio_id": str(portfolio_id),
            "status": status,
            "filled_quantity": filled_quantity,
            "event_type": event_type,
        },
    )
