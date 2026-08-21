import unittest
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.billing.stripe_provider import StripeBillingProvider  # noqa: E402


class StripeCheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.provider = object.__new__(StripeBillingProvider)
        self.provider.price_id = "price_unit"
        self.tenant_id = uuid.uuid4()
        self.attempt_id = uuid.uuid4()

    async def create_checkout(self, **overrides):
        arguments = {
            "tenant_id": self.tenant_id,
            "checkout_attempt_id": self.attempt_id,
            "customer_email": "billing@example.com",
            "customer_id": None,
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/canceled",
            "idempotency_key": f"nexus-checkout-{self.attempt_id}",
            "trial_end": None,
            "trial_period_days": None,
        }
        arguments.update(overrides)
        return await self.provider.create_checkout(**arguments)

    async def test_checkout_sends_fixed_trial_end_and_idempotency_key(self) -> None:
        captured = {}
        trial_end = datetime.now(UTC) + timedelta(days=3)

        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(url="https://checkout.test/session", customer="cus_123")

        with patch("app.billing.stripe_provider.stripe.checkout.Session.create", side_effect=fake_create):
            session = await self.create_checkout(trial_end=trial_end, trial_period_days=9)

        self.assertEqual(session.url, "https://checkout.test/session")
        self.assertEqual(captured["idempotency_key"], f"nexus-checkout-{self.attempt_id}")
        self.assertEqual(captured["subscription_data"]["trial_end"], int(trial_end.timestamp()))
        self.assertNotIn("trial_period_days", captured["subscription_data"])
        self.assertEqual(captured["metadata"]["checkout_attempt_id"], str(self.attempt_id))

    async def test_checkout_uses_trial_period_when_fixed_end_is_absent(self) -> None:
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(url="https://checkout.test/session", customer=None)

        with patch("app.billing.stripe_provider.stripe.checkout.Session.create", side_effect=fake_create):
            await self.create_checkout(trial_period_days=1)

        self.assertEqual(captured["subscription_data"]["trial_period_days"], 1)
        self.assertNotIn("trial_end", captured["subscription_data"])
        self.assertEqual(captured["customer_email"], "billing@example.com")
