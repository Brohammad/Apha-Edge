"""Deployment monitoring and auto-stop."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from alphaedge.shared.infrastructure.celery_app import celery_app


@dataclass(frozen=True)
class DeploymentHealth:
    deployment_id: str
    pnl: Decimal
    drawdown: Decimal
    should_stop: bool
    reason: str | None = None


def evaluate_deployment_health(*, pnl: Decimal, drawdown: Decimal, max_dd: Decimal) -> DeploymentHealth:
    should_stop = drawdown > max_dd
    return DeploymentHealth(
        deployment_id="",
        pnl=pnl,
        drawdown=drawdown,
        should_stop=should_stop,
        reason="Max drawdown breached" if should_stop else None,
    )


@celery_app.task(name="deployment.monitor_active")
def monitor_active_deployments() -> dict:
    return {"checked": 0, "stopped": 0}
