from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class StrategyListing:
    id: UUID
    strategy_id: UUID
    organization_id: UUID
    seller_user_id: UUID
    title: str
    description: str | None
    price_cents: int
    is_public: bool
    clone_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        strategy_id: UUID,
        organization_id: UUID,
        seller_user_id: UUID,
        title: str,
        *,
        description: str | None = None,
        price_cents: int = 0,
        is_public: bool = True,
    ) -> "StrategyListing":
        title = title.strip()
        if not title:
            raise ValidationError("Listing title is required")
        if price_cents < 0:
            raise ValidationError("price_cents cannot be negative")
        return StrategyListing(
            id=uuid4(),
            strategy_id=strategy_id,
            organization_id=organization_id,
            seller_user_id=seller_user_id,
            title=title,
            description=description,
            price_cents=price_cents,
            is_public=is_public,
            clone_count=0,
        )
