from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="optimization.run_optimization", bind=True, max_retries=1)
def run_optimization_task(self, run_id: str) -> None:
    from alphaedge.modules.optimization.infrastructure.runner import run_optimization_sync

    try:
        run_optimization_sync(run_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10) from exc


@celery_app.task(name="optimization.run_trial", bind=True, max_retries=1)
def run_optimization_trial_task(self, run_id: str, trial_id: str) -> None:
    from alphaedge.modules.optimization.infrastructure.runner import (
        run_optimization_trial_sync,
    )

    try:
        run_optimization_trial_sync(run_id, trial_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10) from exc
