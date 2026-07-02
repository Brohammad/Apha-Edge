from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="market_data.run_ingestion", bind=True, max_retries=2)
def run_ingestion_task(self, job_id: str) -> None:
    from alphaedge.modules.market_data.infrastructure.ingestion import run_ingestion_sync

    try:
        run_ingestion_sync(job_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30) from exc
