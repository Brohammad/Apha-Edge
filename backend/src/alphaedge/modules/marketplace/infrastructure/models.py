from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.marketplace.domain.entities import StrategyListing
from alphaedge.modules.marketplace.domain.repositories import StrategyListingRepository
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StrategyListingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "strategy_listings"

    strategy_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    seller_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    price_cents: Mapped[int] = mapped_column(default=0)
    is_public: Mapped[bool] = mapped_column(default=True, index=True)
    clone_count: Mapped[int] = mapped_column(default=0)


def _to_entity(m: StrategyListingModel) -> StrategyListing:
    return StrategyListing(
        id=m.id,
        strategy_id=m.strategy_id,
        organization_id=m.organization_id,
        seller_user_id=m.seller_user_id,
        title=m.title,
        description=m.description,
        price_cents=m.price_cents,
        is_public=m.is_public,
        clone_count=m.clone_count,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyStrategyListingRepository(StrategyListingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, listing: StrategyListing) -> StrategyListing:
        model = StrategyListingModel(
            id=listing.id,
            strategy_id=listing.strategy_id,
            organization_id=listing.organization_id,
            seller_user_id=listing.seller_user_id,
            title=listing.title,
            description=listing.description,
            price_cents=listing.price_cents,
            is_public=listing.is_public,
            clone_count=listing.clone_count,
        )
        self._session.add(model)
        await self._session.flush()
        return listing

    async def get_by_id(self, listing_id: UUID) -> StrategyListing | None:
        model = await self._session.get(StrategyListingModel, listing_id)
        return _to_entity(model) if model else None

    async def list_public(self, *, limit: int = 50, offset: int = 0) -> list[StrategyListing]:
        stmt = (
            select(StrategyListingModel)
            .where(StrategyListingModel.is_public.is_(True))
            .order_by(StrategyListingModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def increment_clone_count(self, listing_id: UUID) -> None:
        model = await self._session.get(StrategyListingModel, listing_id)
        if model:
            model.clone_count += 1
            model.updated_at = datetime.now(UTC)
