from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription, SubscriptionStatus, Tenant, TenantStatus


async def sync_billing_access(db: AsyncSession, tenant: Tenant) -> tuple[Subscription | None, bool]:
    """Return whether automation is billable and expire an ended local trial."""
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription:
        return None, False

    now = datetime.now(UTC)
    trial_active = (
        subscription.status == SubscriptionStatus.TRIALING
        and subscription.trial_ends_at is not None
        and subscription.trial_ends_at > now
    )
    if subscription.status == SubscriptionStatus.TRIALING and not trial_active:
        subscription.status = SubscriptionStatus.INCOMPLETE
        tenant.status = TenantStatus.SUSPENDED
        await db.flush()

    access_allowed = subscription.status == SubscriptionStatus.ACTIVE or trial_active
    if subscription.status == SubscriptionStatus.PAST_DUE and tenant.status == TenantStatus.GRACE_PERIOD:
        access_allowed = True
    return subscription, access_allowed
