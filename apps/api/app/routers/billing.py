from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    return SubscriptionRead.model_validate(subscription, from_attributes=True) if subscription else None


@router.post("/billing/checkout", response_model=BillingSessionRead)
async def create_checkout(tenant: CurrentTenant, user: CurrentUser, db: DbSession, _csrf: CsrfGuard) -> BillingSessionRead:
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if subscription and subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
        raise HTTPException(status_code=409, detail="Tenant já possui assinatura ativa")
    if not subscription:
        subscription = Subscription(tenant_id=tenant.id, provider=settings.billing_provider)
        db.add(subscription)
        await db.flush()
    provider_session = await get_provider().create_checkout(
        tenant_id=tenant.id,
        customer_email=user.email,
        customer_id=subscription.provider_customer_id,
        success_url=f"{settings.frontend_url}/app?checkout=success",
        cancel_url=f"{settings.frontend_url}/app?checkout=canceled",
    )
    if provider_session.customer_id:
        subscription.provider_customer_id = provider_session.customer_id
    await db.commit()
    return BillingSessionRead(url=provider_session.url)


@router.post("/billing/portal", response_model=BillingSessionRead)
async def create_portal(tenant: CurrentTenant, db: DbSession, _csrf: CsrfGuard) -> BillingSessionRead:
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription or not subscription.provider_customer_id:
        raise HTTPException(status_code=404, detail="Assinatura ainda não possui cliente de cobrança")
    session = await get_provider().create_portal(
        customer_id=subscription.provider_customer_id,
        return_url=f"{settings.frontend_url}/app",
    )
    return BillingSessionRead(url=session.url)


def timestamp(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None


async def apply_subscription_state(db: DbSession, data: dict) -> None:
    metadata = data.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    provider_subscription_id = data.get("id")
    subscription = None
    if provider_subscription_id:
        subscription = await db.scalar(
            select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
        )
    if not subscription and tenant_id:
        subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
    if not subscription:
        return
    old_status = subscription.status
    provider_status = data.get("status", "incomplete")
    subscription.status = SubscriptionStatus(provider_status) if provider_status in SubscriptionStatus._value2member_map_ else SubscriptionStatus.INCOMPLETE
    subscription.provider_subscription_id = provider_subscription_id or subscription.provider_subscription_id
    subscription.provider_customer_id = data.get("customer") or subscription.provider_customer_id
    subscription.current_period_end = timestamp(data.get("current_period_end"))
    subscription.cancel_at_period_end = bool(data.get("cancel_at_period_end", False))
    tenant = await db.get(Tenant, subscription.tenant_id)
    if not tenant:
        return
    if subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
        if old_status not in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
            tenant.status = TenantStatus.PROVISIONING
            db.add(OutboxEvent(tenant_id=tenant.id, event_type="tenant.provisioning.requested", payload={"tenant_id": str(tenant.id)}))
    elif subscription.status == SubscriptionStatus.PAST_DUE:
        tenant.status = TenantStatus.GRACE_PERIOD
    elif subscription.status in {SubscriptionStatus.UNPAID, SubscriptionStatus.CANCELED}:
        tenant.status = TenantStatus.SUSPENDED if subscription.status == SubscriptionStatus.UNPAID else TenantStatus.CANCELED


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
    if event.type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        await apply_subscription_state(db, obj)
    elif event.type == "checkout.session.completed":
        tenant_id = (obj.get("metadata") or {}).get("tenant_id") or obj.get("client_reference_id")
        if tenant_id:
            subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
            if subscription:
                subscription.provider_customer_id = obj.get("customer") or subscription.provider_customer_id
                subscription.provider_subscription_id = obj.get("subscription") or subscription.provider_subscription_id
                subscription.status = SubscriptionStatus.INCOMPLETE
    elif event.type == "invoice.paid":
        customer_id = obj.get("customer")
        subscription = await db.scalar(select(Subscription).where(Subscription.provider_customer_id == customer_id))
        if subscription:
            was_active = subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}
            subscription.status = SubscriptionStatus.ACTIVE
            period_end = ((obj.get("lines") or {}).get("data") or [{}])[0].get("period", {}).get("end")
            subscription.current_period_end = timestamp(period_end)
            tenant = await db.get(Tenant, subscription.tenant_id)
            if tenant:
                if not was_active:
                    tenant.status = TenantStatus.PROVISIONING
                    db.add(OutboxEvent(tenant_id=tenant.id, event_type="tenant.provisioning.requested", payload={"tenant_id": str(tenant.id)}))
    elif event.type == "invoice.payment_failed":
        customer_id = obj.get("customer")
        subscription = await db.scalar(select(Subscription).where(Subscription.provider_customer_id == customer_id))
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            tenant = await db.get(Tenant, subscription.tenant_id)
            if tenant:
                tenant.status = TenantStatus.GRACE_PERIOD
    record.processed = True
    await db.commit()
    return {"received": True}
