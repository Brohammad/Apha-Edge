import time

import structlog.contextvars
from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun, task_success

from alphaedge.config import settings

celery_app = Celery(
    "alphaedge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    beat_schedule={
        "compute-all-portfolio-risks-daily": {
            "task": "risk.compute_all_portfolio_risks",
            "schedule": 86400.0,
            "options": {"expires": 3600},
        },
    },
    include=[
        "alphaedge.modules.market_data.infrastructure.tasks",
        "alphaedge.modules.backtesting.infrastructure.tasks",
        "alphaedge.modules.optimization.infrastructure.tasks",
        "alphaedge.modules.execution.infrastructure.order_poller",
        "alphaedge.modules.execution.infrastructure.tasks",
        "alphaedge.modules.insights.infrastructure.tasks",
        "alphaedge.modules.risk.infrastructure.tasks",
        "alphaedge.modules.sec.infrastructure.tasks",
    ],
)

_task_start_times: dict[str, float] = {}


@task_prerun.connect
def on_task_prerun(task_id: str, task, **kwargs) -> None:  # type: ignore[no-untyped-def]
    _task_start_times[task_id] = time.perf_counter()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(task_id=task_id, task_name=task.name)


@task_success.connect
def on_task_success(sender, **kwargs) -> None:  # type: ignore[no-untyped-def]
    from alphaedge.shared.infrastructure.metrics import CELERY_TASK_LATENCY, CELERY_TASKS

    task_id = kwargs.get("task_id") or (sender.request.id if sender else "unknown")
    task_name = sender.name if sender else "unknown"
    CELERY_TASKS.labels(task=task_name, outcome="success").inc()
    start = _task_start_times.pop(task_id, None)
    if start is not None:
        CELERY_TASK_LATENCY.labels(task=task_name).observe(time.perf_counter() - start)


@task_failure.connect
def on_task_failure(sender, task_id: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
    from alphaedge.shared.infrastructure.metrics import CELERY_TASK_LATENCY, CELERY_TASKS

    task_name = sender.name if sender else "unknown"
    CELERY_TASKS.labels(task=task_name, outcome="failure").inc()
    start = _task_start_times.pop(task_id, None)
    if start is not None:
        CELERY_TASK_LATENCY.labels(task=task_name).observe(time.perf_counter() - start)


@task_postrun.connect
def on_task_postrun(task_id: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
    _task_start_times.pop(task_id, None)
