import math
import uuid
from datetime import UTC, datetime, timedelta

import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.billing.access import sync_billing_access
from app.billing.stripe_provider import StripeBillingProvider
from app.config import get_settings
from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import OutboxEvent, Subscription, SubscriptionStatus, Tenant, TenantStatus, WebhookEvent
from app.schemas import BillingSessionRead, SubscriptionRead

router = APIRouter(tags=["billing"])
settings = get_settings()


def get_provider() -> StripeBillingProvider:
    if settings.billing_provider != "stripe":
        raise HTTPException(status_code=503, detail="Provedor de cobrança não suportado")
    try:
        return StripeBillingProvider()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/billing/subscription", response_model=SubscriptionRead | None)
async def read_subscription(tenant: CurrentTenant, db: DbSession) -> SubscriptionRead | None:
    subscription, access_allowed = await sync_billing_access(db, tenant)
    if not subscription:
        return None
    await db.commit()
    now = datetime.now(UTC)
    trial_seconds = max(0.0, (subscription.trial_ends_at - now).total_seconds()) if subscription.trial_ends_at else 0.0
    trial_active = subscription.status == SubscriptionStatus.TRIALING and trial_seconds > 0
    return SubscriptionRead(
        status=subscription.status,
        provider=subscription.provider,
        current_period_end=subscription.current_period_end,
        trial_ends_at=subscription.trial_ends_at,
        grace_ends_at=subscription.grace_ends_at,
        trial_days_remaining=math.ceil(trial_seconds / 86400) if trial_active else 0,
        access_allowed=access_allowed,
        management_available=bool(
            subscription.provider_customer_id and subscription.provider_subscription_id
        ),
        cancel_at_period_end=subscription.cancel_at_period_end,
    )


@router.post("/billing/checkout", response_model=BillingSessionRead)
async def create_checkout(tenant: CurrentTenant, user: CurrentUser, db: DbSession, _csrf: CsrfGuard) -> BillingSessionRead:
    provider = get_provider()
    subscription = await db.scalar(
        select(Subscription).where(Subscription.tenant_id == tenant.id).with_for_update()
    )
    if subscription and subscription.provider_subscription_id and subscription.status != SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma assinatura no provedor. Use o portal de cobrança para gerenciá-la.",
        )
    if subscription and subscription.status in {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.UNPAID,
    }:
        raise HTTPException(
            status_code=409,
            detail="A assinatura existente precisa ser gerenciada no portal de cobrança.",
        )
    if not subscription:
        subscription = Subscription(tenant_id=tenant.id, provider=settings.billing_provider)
        db.add(subscription)
        await db.flush()

    now = datetime.now(UTC)
    attempt_expired = (
        subscription.checkout_attempt_created_at is None
        or subscription.checkout_attempt_created_at <= now - timedelta(hours=24)
    )
    if subscription.checkout_attempt_id is None or attempt_expired:
        subscription.checkout_attempt_id = uuid.uuid4()
        subscription.checkout_attempt_created_at = now
    checkout_attempt_id = subscription.checkout_attempt_id
    attempt_started_at = subscription.checkout_attempt_created_at or now

    trial_end = None
    trial_period_days = None
    if (
        subscription.status == SubscriptionStatus.TRIALING
        and subscription.trial_ends_at
        and subscription.trial_ends_at > attempt_started_at
    ):
        remaining = subscription.trial_ends_at - attempt_started_at
        if remaining >= timedelta(hours=48):
            trial_end = subscription.trial_ends_at
        else:
            trial_period_days = max(1, math.ceil(remaining.total_seconds() / 86400))

    # Persist the operation UUID before contacting Stripe so retries reuse the same key.
    await db.commit()
    try:
        provider_session = await provider.create_checkout(
            tenant_id=tenant.id,
            checkout_attempt_id=checkout_attempt_id,
            customer_email=user.email,
            customer_id=subscription.provider_customer_id,
            success_url=f"{settings.frontend_url}/app?checkout=success",
            cancel_url=f"{settings.frontend_url}/app?checkout=canceled",
            idempotency_key=f"nexus-checkout-{checkout_attempt_id}",
            trial_end=trial_end,
            trial_period_days=trial_period_days,
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível iniciar o pagamento agora") from exc
    if provider_session.customer_id:
        subscription.provider_customer_id = provider_session.customer_id
    await db.commit()
    return BillingSessionRead(url=provider_session.url)


@router.post("/billing/portal", response_model=BillingSessionRead)
async def create_portal(tenant: CurrentTenant, db: DbSession, _csrf: CsrfGuard) -> BillingSessionRead:
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription or not subscription.provider_customer_id:
        raise HTTPException(status_code=404, detail="Assinatura ainda não possui cliente de cobrança")
    try:
        session = await get_provider().create_portal(
            customer_id=subscription.provider_customer_id,
            return_url=f"{settings.frontend_url}/app",
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível abrir o portal de cobrança agora") from exc
    return BillingSessionRead(url=session.url)


def timestamp(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None


def object_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def parse_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def event_is_stale(subscription: Subscription, event_created_at: datetime) -> bool:
    previous = subscription.last_provider_event_created_at
    return previous is not None and event_created_at < previous


def mark_event_applied(subscription: Subscription, event_created_at: datetime) -> None:
    if (
        subscription.last_provider_event_created_at is None
        or event_created_at >= subscription.last_provider_event_created_at
    ):
        subscription.last_provider_event_created_at = event_created_at


def invoice_subscription_id(data: dict) -> str | None:
    parent = data.get("parent") or {}
    subscription_details = parent.get("subscription_details") or {}
    return object_id(subscription_details.get("subscription")) or object_id(data.get("subscription"))


def invoice_period_end(data: dict) -> datetime | None:
    direct = timestamp(data.get("period_end"))
    if direct:
        return direct
    period_ends = [
        line.get("period", {}).get("end")
        for line in ((data.get("lines") or {}).get("data") or [])
        if line.get("period", {}).get("end")
    ]
    return timestamp(max(period_ends)) if period_ends else None


async def apply_subscription_state(db: DbSession, data: dict, event_created_at: datetime) -> bool:
    metadata = data.get("metadata") or {}
    tenant_id = parse_uuid(metadata.get("tenant_id"))
    attempt_id = parse_uuid(metadata.get("checkout_attempt_id"))
    provider_subscription_id = object_id(data.get("id"))
    subscription = None
    if provider_subscription_id:
        subscription = await db.scalar(
            select(Subscription)
            .where(Subscription.provider_subscription_id == provider_subscription_id)
            .with_for_update()
        )
    if not subscription and tenant_id:
        subscription = await db.scalar(
            select(Subscription).where(Subscription.tenant_id == tenant_id).with_for_update()
        )
    if not subscription or event_is_stale(subscription, event_created_at):
        return False
    if (
        provider_subscription_id
        and subscription.provider_subscription_id
        and provider_subscription_id != subscription.provider_subscription_id
    ):
        replacing_canceled_subscription = (
            subscription.status == SubscriptionStatus.CANCELED
            and attempt_id is not None
            and attempt_id == subscription.checkout_attempt_id
        )
        if not replacing_canceled_subscription:
            return False

    old_status = subscription.status
    provider_status = data.get("status", "incomplete")
    subscription.status = SubscriptionStatus(provider_status) if provider_status in SubscriptionStatus._value2member_map_ else SubscriptionStatus.INCOMPLETE
    subscription.provider_subscription_id = provider_subscription_id or subscription.provider_subscription_id
    subscription.provider_customer_id = object_id(data.get("customer")) or subscription.provider_customer_id
    subscription.current_period_end = timestamp(data.get("current_period_end"))
    subscription.trial_ends_at = timestamp(data.get("trial_end")) or subscription.trial_ends_at
    subscription.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
    if attempt_id and attempt_id == subscription.checkout_attempt_id:
        subscription.checkout_attempt_id = None
        subscription.checkout_attempt_created_at = None
    mark_event_applied(subscription, event_created_at)

    tenant = await db.get(Tenant, subscription.tenant_id)
    if not tenant:
        return True
    now = datetime.now(UTC)
    if subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
        subscription.grace_ends_at = None
        if old_status not in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING} or tenant.status in {
            TenantStatus.PENDING_PAYMENT,
            TenantStatus.GRACE_PERIOD,
            TenantStatus.SUSPENDED,
            TenantStatus.CANCELED,
        }:
            tenant.status = TenantStatus.PROVISIONING
            db.add(OutboxEvent(tenant_id=tenant.id, event_type="tenant.provisioning.requested", payload={"tenant_id": str(tenant.id)}))
    elif subscription.status == SubscriptionStatus.PAST_DUE:
        if old_status != SubscriptionStatus.PAST_DUE or subscription.grace_ends_at is None:
            subscription.grace_ends_at = event_created_at + timedelta(days=settings.billing_grace_days)
        tenant.status = TenantStatus.GRACE_PERIOD if subscription.grace_ends_at > now else TenantStatus.SUSPENDED
    elif subscription.status == SubscriptionStatus.CANCELED:
        subscription.grace_ends_at = None
        tenant.status = TenantStatus.CANCELED
    else:
        subscription.grace_ends_at = None
        tenant.status = TenantStatus.SUSPENDED
    return True


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, bool]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook Stripe não configurado")
    raw_body = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(raw_body, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Webhook inválido") from exc
    event_dict = event.to_dict_recursive()
    record = WebhookEvent(provider="stripe", external_event_id=event.id, event_type=event.type, payload=event_dict)
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"received": True}
    obj = event_dict["data"]["object"]
    event_created_at = timestamp(event_dict.get("created")) or datetime.now(UTC)
    if event.type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        await apply_subscription_state(db, obj, event_created_at)
    elif event.type == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        tenant_id = parse_uuid(metadata.get("tenant_id") or obj.get("client_reference_id"))
        if tenant_id:
            subscription = await db.scalar(
                select(Subscription).where(Subscription.tenant_id == tenant_id).with_for_update()
            )
            if subscription:
                attempt_id = parse_uuid(metadata.get("checkout_attempt_id"))
                provider_subscription_id = object_id(obj.get("subscription"))
                attempt_matches = attempt_id is not None and attempt_id == subscription.checkout_attempt_id
                subscription_matches = (
                    provider_subscription_id is not None
                    and provider_subscription_id == subscription.provider_subscription_id
                )
                if obj.get("mode") == "subscription" and (attempt_matches or subscription_matches):
                    subscription.provider_customer_id = object_id(obj.get("customer")) or subscription.provider_customer_id
                    subscription.provider_subscription_id = provider_subscription_id or subscription.provider_subscription_id
                    if attempt_matches:
                        subscription.checkout_attempt_id = None
                        subscription.checkout_attempt_created_at = None
    elif event.type == "invoice.paid":
        provider_subscription_id = invoice_subscription_id(obj)
        subscription = None
        if provider_subscription_id:
            subscription = await db.scalar(
                select(Subscription)
                .where(Subscription.provider_subscription_id == provider_subscription_id)
                .with_for_update()
            )
        customer_id = object_id(obj.get("customer"))
        customer_matches = bool(
            subscription
            and customer_id
            and (
                subscription.provider_customer_id is None
                or subscription.provider_customer_id == customer_id
            )
        )
        if subscription and customer_matches and not event_is_stale(subscription, event_created_at):
            was_active = subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}
            if subscription.status != SubscriptionStatus.CANCELED:
                trial_still_active = (
                    subscription.status == SubscriptionStatus.TRIALING
                    and subscription.trial_ends_at is not None
                    and subscription.trial_ends_at > event_created_at
                )
                if not trial_still_active:
                    subscription.status = SubscriptionStatus.ACTIVE
                subscription.provider_customer_id = customer_id or subscription.provider_customer_id
                subscription.current_period_end = invoice_period_end(obj) or subscription.current_period_end
                subscription.grace_ends_at = None
                mark_event_applied(subscription, event_created_at)
                tenant = await db.get(Tenant, subscription.tenant_id)
                if tenant and (not was_active or tenant.status in {TenantStatus.GRACE_PERIOD, TenantStatus.SUSPENDED}):
                    tenant.status = TenantStatus.PROVISIONING
                    db.add(OutboxEvent(tenant_id=tenant.id, event_type="tenant.provisioning.requested", payload={"tenant_id": str(tenant.id)}))
    elif event.type == "invoice.payment_failed":
        provider_subscription_id = invoice_subscription_id(obj)
        subscription = None
        if provider_subscription_id:
            subscription = await db.scalar(
                select(Subscription)
                .where(Subscription.provider_subscription_id == provider_subscription_id)
                .with_for_update()
            )
        customer_id = object_id(obj.get("customer"))
        customer_matches = bool(
            subscription
            and customer_id
            and (
                subscription.provider_customer_id is None
                or subscription.provider_customer_id == customer_id
            )
        )
        if (
            subscription
            and subscription.status != SubscriptionStatus.CANCELED
            and customer_matches
            and not event_is_stale(subscription, event_created_at)
        ):
            was_past_due = subscription.status == SubscriptionStatus.PAST_DUE
            subscription.status = SubscriptionStatus.PAST_DUE
            subscription.provider_customer_id = customer_id or subscription.provider_customer_id
            if not was_past_due or subscription.grace_ends_at is None:
                subscription.grace_ends_at = event_created_at + timedelta(days=settings.billing_grace_days)
            mark_event_applied(subscription, event_created_at)
            tenant = await db.get(Tenant, subscription.tenant_id)
            if tenant:
                tenant.status = (
                    TenantStatus.GRACE_PERIOD
                    if subscription.grace_ends_at > datetime.now(UTC)
                    else TenantStatus.SUSPENDED
                )
    record.processed = True
    await db.commit()
    return {"received": True}
