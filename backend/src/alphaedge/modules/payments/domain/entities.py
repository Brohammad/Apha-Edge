from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class PurchaseStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class MarketplacePurchase:
    id: UUID
    listing_id: UUID
    buyer_user_id: UUID
    amount_cents: int
    status: PurchaseStatus
    stripe_session_id: str | None
    completed_at: datetime | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        listing_id: UUID,
        buyer_user_id: UUID,
        amount_cents: int,
        *,
        stripe_session_id: str | None = None,
    ) -> "MarketplacePurchase":
        return MarketplacePurchase(
            id=uuid4(),
            listing_id=listing_id,
            buyer_user_id=buyer_user_id,
            amount_cents=amount_cents,
            status=PurchaseStatus.PENDING,
            stripe_session_id=stripe_session_id,
            completed_at=None,
        )

    def mark_completed(self) -> None:
        self.status = PurchaseStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
