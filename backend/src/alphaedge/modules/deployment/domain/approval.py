"""Live deployment approval workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class DeploymentApproval:
    id: UUID
    deployment_id: UUID
    reviewer_id: UUID | None
    status: ApprovalStatus
    notes: str = ""
    created_at: datetime = datetime.now(UTC)

    @staticmethod
    def create(deployment_id: UUID) -> "DeploymentApproval":
        return DeploymentApproval(id=uuid4(), deployment_id=deployment_id, reviewer_id=None, status=ApprovalStatus.PENDING)

    def approve(self, reviewer_id: UUID, notes: str = "") -> None:
        self.status = ApprovalStatus.APPROVED
        self.reviewer_id = reviewer_id
        self.notes = notes

    def reject(self, reviewer_id: UUID, notes: str) -> None:
        self.status = ApprovalStatus.REJECTED
        self.reviewer_id = reviewer_id
        self.notes = notes
