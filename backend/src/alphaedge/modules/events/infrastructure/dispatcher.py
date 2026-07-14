"""Outbox dispatcher Celery worker."""

import asyncio

from alphaedge.shared.infrastructure.celery_app import celery_app
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.infrastructure.outbox import fetch_unprocessed_events, mark_event_processed
from alphaedge.modules.events.infrastructure.subscribers import dispatch_event


@celery_app.task(name="events.dispatch_outbox")
def dispatch_outbox(batch_size: int = 50) -> dict:
    return asyncio.run(_dispatch_async(batch_size))


async def _dispatch_async(batch_size: int) -> dict:
    processed = 0
    async with async_session_factory() as session:
        events = await fetch_unprocessed_events(session, limit=batch_size)
        for event in events:
            await dispatch_event(event.event_type, event.payload)
            await mark_event_processed(session, event.id)
            processed += 1
        await session.commit()
    return {"processed": processed}
