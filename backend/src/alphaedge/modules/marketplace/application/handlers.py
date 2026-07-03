from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alphaedge.modules.marketplace.domain.entities import StrategyListing
from alphaedge.modules.marketplace.domain.repositories import StrategyListingRepository
from alphaedge.modules.organization.domain.repositories import OrganizationMemberRepository
from alphaedge.modules.strategy.domain.enums import VersionStatus
from alphaedge.modules.strategy.domain.repositories import (
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.modules.strategy.domain.value_objects import Strategy, StrategyVersion
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


@dataclass(frozen=True)
class PublishListingCommand:
    user_id: UUID
    strategy_id: UUID
    organization_id: UUID
    title: str
    description: str | None
    price_cents: int


@dataclass(frozen=True)
class CloneListingCommand:
    user_id: UUID
    listing_id: UUID


@dataclass(frozen=True)
class ListingDTO:
    id: UUID
    strategy_id: UUID
    organization_id: UUID
    title: str
    description: str | None
    price_cents: int
    clone_count: int
    created_at: datetime

    @staticmethod
    def from_entity(entity: StrategyListing) -> "ListingDTO":
        return ListingDTO(
            id=entity.id,
            strategy_id=entity.strategy_id,
            organization_id=entity.organization_id,
            title=entity.title,
            description=entity.description,
            price_cents=entity.price_cents,
            clone_count=entity.clone_count,
            created_at=entity.created_at,
        )


class PublishListingHandler:
    def __init__(
        self,
        listing_repo: StrategyListingRepository,
        strategy_repo: StrategyRepository,
        member_repo: OrganizationMemberRepository,
    ) -> None:
        self._listing_repo = listing_repo
        self._strategy_repo = strategy_repo
        self._member_repo = member_repo

    async def handle(self, command: PublishListingCommand) -> ListingDTO:
        strategy = await self._strategy_repo.get_by_id(command.strategy_id)
        if not strategy or strategy.deleted_at is not None:
            raise NotFoundError("Strategy", str(command.strategy_id))
        if strategy.user_id != command.user_id:
            raise AuthorizationError("You do not own this strategy")
        if not await self._member_repo.is_member(command.organization_id, command.user_id):
            raise AuthorizationError("You are not a member of this organization")

        listing = StrategyListing.create(
            strategy_id=command.strategy_id,
            organization_id=command.organization_id,
            seller_user_id=command.user_id,
            title=command.title,
            description=command.description,
            price_cents=command.price_cents,
        )
        saved = await self._listing_repo.save(listing)
        return ListingDTO.from_entity(saved)


class ListPublicListingsHandler:
    def __init__(self, listing_repo: StrategyListingRepository) -> None:
        self._listing_repo = listing_repo

    async def handle(self, *, limit: int = 50, offset: int = 0) -> list[ListingDTO]:
        items = await self._listing_repo.list_public(limit=limit, offset=offset)
        return [ListingDTO.from_entity(i) for i in items]


class CloneListingHandler:
    def __init__(
        self,
        listing_repo: StrategyListingRepository,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._listing_repo = listing_repo
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: CloneListingCommand) -> dict[str, str]:
        listing = await self._listing_repo.get_by_id(command.listing_id)
        if not listing or not listing.is_public:
            raise NotFoundError("StrategyListing", str(command.listing_id))

        source = await self._strategy_repo.get_by_id(listing.strategy_id)
        if not source or source.deleted_at is not None:
            raise ValidationError("Source strategy is no longer available")

        versions = await self._version_repo.list_by_strategy(listing.strategy_id)
        if not versions:
            raise ValidationError("Source strategy has no versions")
        latest = max(versions, key=lambda v: v.version)

        cloned = Strategy.create(
            user_id=command.user_id,
            name=f"{source.name} (clone)",
            strategy_type=source.strategy_type,
            description=source.description,
        )
        await self._strategy_repo.save(cloned)

        new_version = StrategyVersion.create(
            strategy_id=cloned.id,
            version=1,
            source_code=latest.source_code,
            parameters=dict(latest.parameters),
        )
        new_version.status = VersionStatus.DRAFT
        new_version.compiled_hash = latest.compiled_hash
        await self._version_repo.save(new_version)
        await self._listing_repo.increment_clone_count(listing.id)

        return {"strategy_id": str(cloned.id), "name": cloned.name}
