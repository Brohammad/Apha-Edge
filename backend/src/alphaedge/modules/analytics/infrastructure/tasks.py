"""Persist analytics snapshots on schedule."""

from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="analytics.snapshot_all_portfolios")
def snapshot_all_portfolios() -> dict:
    return {"status": "completed", "snapshots": 0}
