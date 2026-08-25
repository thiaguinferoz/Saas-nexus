from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Subscription, SubscriptionStatus, Tenant, TenantStatus

settings = get_settings()


async def sync_billing_access(db: AsyncSession, tenant: Tenant) -> tuple[Subscription | None, bool]:
    """Return whether automation is billable and persist trial/grace expiration."""
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription:
        return None, False

    now = datetime.now(UTC)
    trial_active = (
        subscription.status == SubscriptionStatus.TRIALING
        and subscription.trial_ends_at is not None
        and subscription.trial_ends_at > now
    )
    changed = False
    paid_period_expired = (
        subscription.status == SubscriptionStatus.ACTIVE
        and subscription.current_period_end is not None
        and subscription.current_period_end <= now
    )
    if paid_period_expired:
        subscription.status = SubscriptionStatus.INCOMPLETE
        tenant.status = TenantStatus.SUSPENDED
        changed = True
    if subscription.status == SubscriptionStatus.TRIALING and not trial_active:
        subscription.status = SubscriptionStatus.INCOMPLETE
        tenant.status = TenantStatus.SUSPENDED
        changed = True

    access_allowed = subscription.status == SubscriptionStatus.ACTIVE or trial_active
    if subscription.status == SubscriptionStatus.PAST_DUE:
        if subscription.grace_ends_at is None:
            subscription.grace_ends_at = now + timedelta(days=settings.billing_grace_days)
            changed = True
        grace_active = subscription.grace_ends_at > now
        desired_status = TenantStatus.GRACE_PERIOD if grace_active else TenantStatus.SUSPENDED
        if tenant.status != desired_status:
            tenant.status = desired_status
            changed = True
        access_allowed = grace_active
    if changed:
        await db.flush()
    return subscription, access_allowed
