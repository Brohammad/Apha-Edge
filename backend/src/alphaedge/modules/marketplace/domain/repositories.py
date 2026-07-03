from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.marketplace.domain.entities import StrategyListing


class StrategyListingRepository(ABC):
    @abstractmethod
    async def save(self, listing: StrategyListing) -> StrategyListing: ...

    @abstractmethod
    async def get_by_id(self, listing_id: UUID) -> StrategyListing | None: ...

    @abstractmethod
    async def list_public(self, *, limit: int = 50, offset: int = 0) -> list[StrategyListing]: ...

    @abstractmethod
    async def increment_clone_count(self, listing_id: UUID) -> None: ...
