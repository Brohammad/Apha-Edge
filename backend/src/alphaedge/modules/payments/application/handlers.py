from dataclasses import dataclass
from uuid import UUID

from alphaedge.modules.marketplace.domain.repositories import StrategyListingRepository
from alphaedge.modules.payments.domain.entities import MarketplacePurchase
from alphaedge.modules.payments.domain.repositories import MarketplacePurchaseRepository
from alphaedge.modules.payments.infrastructure.stripe_gateway import create_checkout_session
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


@dataclass(frozen=True)
class CreateCheckoutCommand:
    user_id: UUID
    listing_id: UUID
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CompleteMockCheckoutCommand:
    user_id: UUID
    session_id: str


@dataclass(frozen=True)
class CheckoutDTO:
    session_id: str
    checkout_url: str
    already_purchased: bool
    mock: bool


class CreateListingCheckoutHandler:
    def __init__(
        self,
        listing_repo: StrategyListingRepository,
        purchase_repo: MarketplacePurchaseRepository,
    ) -> None:
        self._listing_repo = listing_repo
        self._purchase_repo = purchase_repo

    async def handle(self, command: CreateCheckoutCommand) -> CheckoutDTO:
        listing = await self._listing_repo.get_by_id(command.listing_id)
        if not listing or not listing.is_public:
            raise NotFoundError("StrategyListing", str(command.listing_id))

        if listing.price_cents == 0:
            return CheckoutDTO(
                session_id="",
                checkout_url="",
                already_purchased=True,
                mock=False,
            )

        if listing.seller_user_id == command.user_id:
            raise AuthorizationError("You cannot purchase your own listing")

        if await self._purchase_repo.has_completed_purchase(listing.id, command.user_id):
            return CheckoutDTO(
                session_id="",
                checkout_url="",
                already_purchased=True,
                mock=False,
            )

        session = create_checkout_session(
            listing_id=str(listing.id),
            title=listing.title,
            amount_cents=listing.price_cents,
            success_url=command.success_url,
            cancel_url=command.cancel_url,
        )

        purchase = MarketplacePurchase.create(
            listing.id,
            command.user_id,
            listing.price_cents,
            stripe_session_id=session.session_id,
        )
        await self._purchase_repo.save(purchase)

        return CheckoutDTO(
            session_id=session.session_id,
            checkout_url=session.checkout_url,
            already_purchased=False,
            mock=session.mock,
        )


class CompleteMockCheckoutHandler:
    def __init__(self, purchase_repo: MarketplacePurchaseRepository) -> None:
        self._purchase_repo = purchase_repo

    async def handle(self, command: CompleteMockCheckoutCommand) -> dict[str, str]:
        if not command.session_id.startswith("mock_"):
            raise ValidationError("Only mock checkout sessions can be completed via API")
        purchase = await self._purchase_repo.get_by_session_id(command.session_id)
        if not purchase:
            raise NotFoundError("MarketplacePurchase", command.session_id)
        if purchase.buyer_user_id != command.user_id:
            raise AuthorizationError("This checkout belongs to another user")
        if purchase.status.value != "completed":
            purchase.mark_completed()
            await self._purchase_repo.update(purchase)
        return {"status": "completed", "listing_id": str(purchase.listing_id)}


class StripeWebhookHandler:
    def __init__(self, purchase_repo: MarketplacePurchaseRepository) -> None:
        self._purchase_repo = purchase_repo

    async def handle(self, payload: bytes, signature: str | None) -> dict[str, str]:
        from alphaedge.config import settings

        if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
            return {"status": "ignored"}

        import stripe

        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(
            payload, signature or "", settings.stripe_webhook_secret
        )
        if event["type"] != "checkout.session.completed":
            return {"status": "ignored"}

        session = event["data"]["object"]
        session_id = str(session.get("id", ""))
        purchase = await self._purchase_repo.get_by_session_id(session_id)
        if purchase and purchase.status.value != "completed":
            purchase.mark_completed()
            await self._purchase_repo.update(purchase)
        return {"status": "processed"}
