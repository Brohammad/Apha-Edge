"""Team workspaces with review workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


@dataclass
class TeamWorkspace:
    id: UUID
    name: str
    owner_id: UUID
    member_ids: list[UUID] = field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(name: str, owner_id: UUID) -> "TeamWorkspace":
        return TeamWorkspace(id=uuid4(), name=name, owner_id=owner_id, member_ids=[owner_id])

    def submit_for_review(self) -> None:
        self.review_status = ReviewStatus.IN_REVIEW

    def approve(self) -> None:
        self.review_status = ReviewStatus.APPROVED
