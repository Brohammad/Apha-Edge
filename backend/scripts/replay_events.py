#!/usr/bin/env python3
"""Replay outbox events for debugging."""

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from alphaedge.modules.events.infrastructure.subscribers import dispatch_event
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.infrastructure.outbox import OutboxEventModel


async def replay(*, event_id: str | None, limit: int) -> int:
    count = 0
    async with async_session_factory() as session:
        stmt = select(OutboxEventModel).order_by(OutboxEventModel.created_at.desc()).limit(limit)
        if event_id:
            stmt = select(OutboxEventModel).where(OutboxEventModel.id == UUID(event_id))
        result = await session.execute(stmt)
        for event in result.scalars():
            await dispatch_event(event.event_type, event.payload)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay outbox domain events")
    parser.add_argument("--event-id", default=None)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    n = asyncio.run(replay(event_id=args.event_id, limit=args.limit))
    print(f"Replayed {n} event(s)")


if __name__ == "__main__":
    main()
