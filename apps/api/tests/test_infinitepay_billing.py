import unittest
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.billing.infinitepay_provider import InfinitePayPayment  # noqa: E402
from app.models import BillingOrder, Subscription, SubscriptionStatus, Tenant, TenantStatus, WebhookEvent  # noqa: E402
from app.routers.billing import apply_infinitepay_payment  # noqa: E402


class FakeInfinitePaySession:
    def __init__(self, subscription: Subscription, tenant: Tenant) -> None:
        self.subscription = subscription
        self.tenant = tenant
        self.scalar_calls = 0
        self.added = []
        self.commits = 0

    async def scalar(self, _statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return None
        return self.subscription

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def get(self, _model, _identifier):
        return self.tenant

    async def commit(self) -> None:
        self.commits += 1


class InfinitePayBillingTests(unittest.IsolatedAsyncioTestCase):
    async def test_paid_plan_starts_at_payment_and_does_not_append_trial(self) -> None:
        tenant_id = uuid.uuid4()
        subscription = Subscription(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider="infinitepay",
            status=SubscriptionStatus.TRIALING,
            trial_ends_at=datetime.now(UTC) + timedelta(days=20),
            current_period_end=datetime.now(UTC) + timedelta(days=20),
        )
        tenant = Tenant(id=tenant_id, name="Nexus Test", slug="nexus-test", status=TenantStatus.ACTIVE)
        order = BillingOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            provider="infinitepay",
            plan_code="common",
            billing_interval="monthly",
            amount_cents=60_000,
            status="pending",
        )
        payment = InfinitePayPayment(True, 60_000, 60_000, 1, "pix")
        db = FakeInfinitePaySession(subscription, tenant)
        before = datetime.now(UTC)

        await apply_infinitepay_payment(
            db,
            order=order,
            transaction_nsu="transaction-1",
            invoice_slug="invoice-1",
            payment=payment,
            event_payload={"order_nsu": f"nexus-{order.id}"},
        )

        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.plan_code, "common")
        self.assertEqual(subscription.billing_interval, "monthly")
        self.assertEqual(subscription.last_payment_method, "pix")
        self.assertGreater(subscription.current_period_end, before + timedelta(days=27))
        self.assertLess(subscription.current_period_end, before + timedelta(days=35))
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.provider_transaction_id, "transaction-1")
        self.assertTrue(any(isinstance(item, WebhookEvent) and item.processed for item in db.added))
        self.assertEqual(db.commits, 1)

    async def test_wrong_amount_never_activates_order(self) -> None:
        tenant_id = uuid.uuid4()
        subscription = Subscription(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider="infinitepay",
            status=SubscriptionStatus.INCOMPLETE,
        )
        tenant = Tenant(id=tenant_id, name="Nexus Test", slug="nexus-test-2", status=TenantStatus.SUSPENDED)
        order = BillingOrder(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            provider="infinitepay",
            plan_code="custom",
            billing_interval="annual",
            amount_cents=900_000,
            status="pending",
        )
        db = FakeInfinitePaySession(subscription, tenant)

        with self.assertRaises(HTTPException) as raised:
            await apply_infinitepay_payment(
                db,
                order=order,
                transaction_nsu="transaction-wrong",
                invoice_slug="invoice-wrong",
                payment=InfinitePayPayment(True, 60_000, 60_000, 1, "pix"),
                event_payload={},
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(order.status, "pending")
        self.assertEqual(subscription.status, SubscriptionStatus.INCOMPLETE)
        self.assertEqual(db.commits, 0)
