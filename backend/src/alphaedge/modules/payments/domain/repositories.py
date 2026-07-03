from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.payments.domain.entities import MarketplacePurchase


class MarketplacePurchaseRepository(ABC):
    @abstractmethod
    async def save(self, purchase: MarketplacePurchase) -> MarketplacePurchase:
        pass

    @abstractmethod
    async def get_by_id(self, purchase_id: UUID) -> MarketplacePurchase | None:
        pass

    @abstractmethod
    async def get_by_session_id(self, session_id: str) -> MarketplacePurchase | None:
        pass

    @abstractmethod
    async def has_completed_purchase(self, listing_id: UUID, buyer_user_id: UUID) -> bool:
        pass

    @abstractmethod
    async def update(self, purchase: MarketplacePurchase) -> MarketplacePurchase:
        pass
