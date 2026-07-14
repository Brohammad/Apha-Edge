"""Enable live broker strategy deployments after approval."""

from __future__ import annotations

from uuid import UUID

from alphaedge.modules.deployment.domain.approval import ApprovalStatus, DeploymentApproval
from alphaedge.shared.domain.exceptions import ValidationError


def can_deploy_live(approval: DeploymentApproval | None, *, live_trading_enabled: bool) -> bool:
    if not live_trading_enabled:
        raise ValidationError("Live trading is disabled platform-wide")
    if approval is None or approval.status != ApprovalStatus.APPROVED:
        raise ValidationError("Deployment requires risk review approval")
    return True


def mark_deployment_live(deployment_id: UUID) -> dict:
    return {"deployment_id": str(deployment_id), "mode": "live", "status": "active"}
