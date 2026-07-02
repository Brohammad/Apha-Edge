from celery import Celery

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
    include=[
        "alphaedge.modules.market_data.infrastructure.tasks",
        "alphaedge.modules.backtesting.infrastructure.tasks",
        "alphaedge.modules.optimization.infrastructure.tasks",
        "alphaedge.modules.execution.infrastructure.tasks",
        "alphaedge.modules.insights.infrastructure.tasks",
        "alphaedge.modules.risk.infrastructure.tasks",
    ],
)
