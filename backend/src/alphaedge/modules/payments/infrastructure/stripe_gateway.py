"""Stripe checkout — uses real Stripe when configured, mock flow otherwise."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from alphaedge.config import settings


@dataclass(frozen=True)
class CheckoutSession:
    session_id: str
    checkout_url: str
    mock: bool = False


def create_checkout_session(
    *,
    listing_id: str,
    title: str,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
) -> CheckoutSession:
    if settings.stripe_secret_key:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {"name": title},
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"listing_id": listing_id},
        )
        return CheckoutSession(
            session_id=str(session.id),
            checkout_url=str(session.url),
        )

    session_id = f"mock_{uuid4().hex}"
    base = settings.oauth_frontend_callback_url.rsplit("/", 1)[0]
    checkout_url = f"{base}/marketplace?mock_checkout={session_id}&listing_id={listing_id}"
    return CheckoutSession(session_id=session_id, checkout_url=checkout_url, mock=True)
