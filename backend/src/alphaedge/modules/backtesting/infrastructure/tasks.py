from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="backtesting.run_backtest", bind=True, max_retries=1)
def run_backtest_task(self, run_id: str) -> None:
    from alphaedge.modules.backtesting.infrastructure.runner import run_backtest_sync

    try:
        run_backtest_sync(run_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10) from exc
