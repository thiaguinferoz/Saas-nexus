import unittest
import uuid
from datetime import UTC, datetime, timedelta

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.models import Subscription, SubscriptionStatus  # noqa: E402
from app.routers.billing import event_is_stale, invoice_subscription_id, mark_event_applied  # noqa: E402


class BillingWebhookHelperTests(unittest.TestCase):
    def test_invoice_subscription_id_reads_modern_parent_shape(self) -> None:
        invoice = {
            "subscription": "sub_legacy_should_not_win",
            "parent": {
                "subscription_details": {
                    "subscription": "sub_from_parent",
                }
            },
        }

        self.assertEqual(invoice_subscription_id(invoice), "sub_from_parent")

    def test_invoice_subscription_id_falls_back_to_top_level_shape(self) -> None:
        invoice = {"subscription": {"id": "sub_top_level"}}

        self.assertEqual(invoice_subscription_id(invoice), "sub_top_level")

    def test_stale_event_does_not_replace_newer_provider_timestamp(self) -> None:
        newer_timestamp = datetime.now(UTC)
        older_timestamp = newer_timestamp - timedelta(minutes=5)
        subscription = Subscription(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            provider="stripe",
            status=SubscriptionStatus.ACTIVE,
            last_provider_event_created_at=newer_timestamp,
        )

        self.assertTrue(event_is_stale(subscription, older_timestamp))

        mark_event_applied(subscription, older_timestamp)

        self.assertEqual(subscription.last_provider_event_created_at, newer_timestamp)
