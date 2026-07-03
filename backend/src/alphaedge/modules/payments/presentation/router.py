from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.config import settings
from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.marketplace.infrastructure.models import SQLAlchemyStrategyListingRepository
from alphaedge.modules.payments.application.handlers import (
    CompleteMockCheckoutCommand,
    CompleteMockCheckoutHandler,
    CreateCheckoutCommand,
    CreateListingCheckoutHandler,
    StripeWebhookHandler,
)
from alphaedge.modules.payments.infrastructure.models import (
    SQLAlchemyMarketplacePurchaseRepository,
)
from alphaedge.shared.presentation.envelope import success_response

payments_router = APIRouter(prefix="/payments", tags=["Payments"])


class MockCompleteRequest(BaseModel):
    session_id: str


@payments_router.post("/marketplace/listings/{listing_id}/checkout")
async def create_listing_checkout(
    listing_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    listing_repo = SQLAlchemyStrategyListingRepository(session)
    purchase_repo = SQLAlchemyMarketplacePurchaseRepository(session)
    handler = CreateListingCheckoutHandler(listing_repo, purchase_repo)

    frontend_base = settings.oauth_frontend_callback_url.rsplit("/", 1)[0]
    result = await handler.handle(
        CreateCheckoutCommand(
            user_id=user_id,
            listing_id=listing_id,
            success_url=f"{frontend_base}/marketplace?purchased={listing_id}",
            cancel_url=f"{frontend_base}/marketplace",
        )
    )
    return success_response(
        {
            "session_id": result.session_id,
            "checkout_url": result.checkout_url,
            "already_purchased": result.already_purchased,
            "mock": result.mock,
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@payments_router.post("/mock/complete")
async def complete_mock_checkout(
    body: MockCompleteRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    purchase_repo = SQLAlchemyMarketplacePurchaseRepository(session)
    handler = CompleteMockCheckoutHandler(purchase_repo)
    result = await handler.handle(
        CompleteMockCheckoutCommand(user_id=user_id, session_id=body.session_id)
    )
    await session.commit()
    return success_response(result, request_id=getattr(request.state, "request_id", ""))


@payments_router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_db_session),
):
    purchase_repo = SQLAlchemyMarketplacePurchaseRepository(session)
    handler = StripeWebhookHandler(purchase_repo)
    payload = await request.body()
    result = await handler.handle(payload, stripe_signature)
    await session.commit()
    return result
