from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="execution.process_order", bind=True, max_retries=3)
def process_order_task(self, order_id: str) -> None:
    from alphaedge.modules.execution.infrastructure.runner import (
        TransientOrderError,
        run_order_sync,
    )

    try:
        run_order_sync(order_id)
    except TransientOrderError as exc:
        countdown = min(60, 2**self.request.retries * 5)
        raise self.retry(exc=exc, countdown=countdown) from exc
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10) from exc
