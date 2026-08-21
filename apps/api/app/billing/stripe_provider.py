import uuid
from datetime import datetime

import stripe
from anyio import to_thread

from app.billing.provider import BillingSession
from app.config import get_settings


class StripeBillingProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.stripe_secret_key or not settings.stripe_price_id:
            raise RuntimeError("Stripe não configurado")
        stripe.api_key = settings.stripe_secret_key
        self.price_id = settings.stripe_price_id

    async def create_checkout(
        self,
        *,
        tenant_id: uuid.UUID,
        checkout_attempt_id: uuid.UUID,
        customer_email: str,
        customer_id: str | None,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
        trial_end: datetime | None,
        trial_period_days: int | None,
    ) -> BillingSession:
        params: dict = {
            "mode": "subscription",
            "line_items": [{"price": self.price_id, "quantity": 1}],
            "client_reference_id": str(tenant_id),
            "metadata": {"tenant_id": str(tenant_id), "checkout_attempt_id": str(checkout_attempt_id)},
            "subscription_data": {
                "metadata": {"tenant_id": str(tenant_id), "checkout_attempt_id": str(checkout_attempt_id)}
            },
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": True,
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = customer_email
        if trial_end:
            params["subscription_data"]["trial_end"] = int(trial_end.timestamp())
        elif trial_period_days:
            params["subscription_data"]["trial_period_days"] = trial_period_days
        session = await to_thread.run_sync(
            lambda: stripe.checkout.Session.create(**params, idempotency_key=idempotency_key)
        )
        return BillingSession(url=session.url, customer_id=session.customer)

    async def create_portal(self, *, customer_id: str, return_url: str) -> BillingSession:
        session = await to_thread.run_sync(
            lambda: stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        )
        return BillingSession(url=session.url, customer_id=customer_id)
