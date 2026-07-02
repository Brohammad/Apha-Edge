from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="insights.generate", bind=True, max_retries=2)
def generate_insight_task(self, request_id: str) -> None:
    from alphaedge.modules.insights.infrastructure.runner import run_insight_sync

    try:
        run_insight_sync(request_id)
    except Exception as exc:
        countdown = min(60, 2 ** self.request.retries * 10)
        raise self.retry(exc=exc, countdown=countdown) from exc
