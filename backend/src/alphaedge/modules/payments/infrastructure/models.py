from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.payments.domain.entities import MarketplacePurchase, PurchaseStatus
from alphaedge.modules.payments.domain.repositories import MarketplacePurchaseRepository
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MarketplacePurchaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketplace_purchases"

    listing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    buyer_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default=PurchaseStatus.PENDING.value)
    stripe_session_id: Mapped[str | None] = mapped_column(nullable=True, unique=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _to_entity(m: MarketplacePurchaseModel) -> MarketplacePurchase:
    return MarketplacePurchase(
        id=m.id,
        listing_id=m.listing_id,
        buyer_user_id=m.buyer_user_id,
        amount_cents=m.amount_cents,
        status=PurchaseStatus(m.status),
        stripe_session_id=m.stripe_session_id,
        completed_at=m.completed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyMarketplacePurchaseRepository(MarketplacePurchaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, purchase: MarketplacePurchase) -> MarketplacePurchase:
        model = MarketplacePurchaseModel(
            id=purchase.id,
            listing_id=purchase.listing_id,
            buyer_user_id=purchase.buyer_user_id,
            amount_cents=purchase.amount_cents,
            status=purchase.status.value,
            stripe_session_id=purchase.stripe_session_id,
            completed_at=purchase.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return purchase

    async def get_by_id(self, purchase_id: UUID) -> MarketplacePurchase | None:
        model = await self._session.get(MarketplacePurchaseModel, purchase_id)
        return _to_entity(model) if model else None

    async def get_by_session_id(self, session_id: str) -> MarketplacePurchase | None:
        stmt = select(MarketplacePurchaseModel).where(
            MarketplacePurchaseModel.stripe_session_id == session_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def has_completed_purchase(self, listing_id: UUID, buyer_user_id: UUID) -> bool:
        stmt = select(MarketplacePurchaseModel.id).where(
            MarketplacePurchaseModel.listing_id == listing_id,
            MarketplacePurchaseModel.buyer_user_id == buyer_user_id,
            MarketplacePurchaseModel.status == PurchaseStatus.COMPLETED.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update(self, purchase: MarketplacePurchase) -> MarketplacePurchase:
        model = await self._session.get(MarketplacePurchaseModel, purchase.id)
        if not model:
            raise ValueError("Purchase not found")
        model.status = purchase.status.value
        model.stripe_session_id = purchase.stripe_session_id
        model.completed_at = purchase.completed_at
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return purchase
