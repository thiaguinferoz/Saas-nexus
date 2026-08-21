import unittest
import uuid
from datetime import UTC, datetime, timedelta

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.billing.access import sync_billing_access  # noqa: E402
from app.models import Subscription, SubscriptionStatus, Tenant, TenantStatus  # noqa: E402


class FakeBillingSession:
    def __init__(self, subscription: Subscription | None) -> None:
        self.subscription = subscription
        self.flush_count = 0

    async def scalar(self, _statement):
        return self.subscription

    async def flush(self) -> None:
        self.flush_count += 1


def tenant_with(status: TenantStatus = TenantStatus.ACTIVE) -> Tenant:
    return Tenant(id=uuid.uuid4(), name="Test tenant", slug=f"tenant-{uuid.uuid4().hex}", status=status)


def subscription_for(tenant: Tenant, *, status: SubscriptionStatus) -> Subscription:
    return Subscription(id=uuid.uuid4(), tenant_id=tenant.id, status=status, provider="stripe")


class BillingAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_local_trial_allows_access(self) -> None:
        tenant = tenant_with()
        subscription = subscription_for(tenant, status=SubscriptionStatus.TRIALING)
        subscription.trial_ends_at = datetime.now(UTC) + timedelta(days=2)
        db = FakeBillingSession(subscription)

        _, access_allowed = await sync_billing_access(db, tenant)

        self.assertTrue(access_allowed)
        self.assertEqual(subscription.status, SubscriptionStatus.TRIALING)
        self.assertEqual(db.flush_count, 0)

    async def test_expired_trial_suspends_tenant_and_denies_access(self) -> None:
        tenant = tenant_with()
        subscription = subscription_for(tenant, status=SubscriptionStatus.TRIALING)
        subscription.trial_ends_at = datetime.now(UTC) - timedelta(seconds=1)
        db = FakeBillingSession(subscription)

        _, access_allowed = await sync_billing_access(db, tenant)

        self.assertFalse(access_allowed)
        self.assertEqual(subscription.status, SubscriptionStatus.INCOMPLETE)
        self.assertEqual(tenant.status, TenantStatus.SUSPENDED)
        self.assertEqual(db.flush_count, 1)

    async def test_first_past_due_check_starts_bounded_grace_period(self) -> None:
        tenant = tenant_with(TenantStatus.ACTIVE)
        subscription = subscription_for(tenant, status=SubscriptionStatus.PAST_DUE)
        subscription.grace_ends_at = None
        db = FakeBillingSession(subscription)
        before = datetime.now(UTC)

        _, access_allowed = await sync_billing_access(db, tenant)

        self.assertTrue(access_allowed)
        self.assertEqual(tenant.status, TenantStatus.GRACE_PERIOD)
        self.assertIsNotNone(subscription.grace_ends_at)
        self.assertGreater(subscription.grace_ends_at, before)
        self.assertEqual(db.flush_count, 1)

    async def test_expired_grace_period_suspends_tenant(self) -> None:
        tenant = tenant_with(TenantStatus.GRACE_PERIOD)
        subscription = subscription_for(tenant, status=SubscriptionStatus.PAST_DUE)
        subscription.grace_ends_at = datetime.now(UTC) - timedelta(seconds=1)
        db = FakeBillingSession(subscription)

        _, access_allowed = await sync_billing_access(db, tenant)

        self.assertFalse(access_allowed)
        self.assertEqual(tenant.status, TenantStatus.SUSPENDED)
        self.assertEqual(db.flush_count, 1)
