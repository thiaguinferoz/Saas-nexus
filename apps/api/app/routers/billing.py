import math
import uuid
from calendar import monthrange
from datetime import UTC, datetime, timedelta

import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.billing.access import sync_billing_access
from app.billing.infinitepay_provider import (
    InfinitePayBillingProvider,
    InfinitePayError,
    InfinitePayPayment,
    get_plan_offer,
)
from app.billing.stripe_provider import StripeBillingProvider
from app.config import get_settings
from app.dependencies import CsrfGuard, CurrentTenant, CurrentUser, DbSession
from app.models import BillingOrder, OutboxEvent, Subscription, SubscriptionStatus, Tenant, TenantStatus, WebhookEvent
from app.schemas import BillingCheckoutCreate, BillingSessionRead, InfinitePayVerificationRequest, SubscriptionRead

router = APIRouter(tags=["billing"])
settings = get_settings()


def get_stripe_provider() -> StripeBillingProvider:
    if settings.billing_provider != "stripe":
        raise HTTPException(status_code=503, detail="Provedor de cobrança não suportado")
    try:
        return StripeBillingProvider()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_infinitepay_provider() -> InfinitePayBillingProvider:
    if settings.billing_provider != "infinitepay":
        raise HTTPException(status_code=503, detail="InfinitePay não está ativa")
    try:
        return InfinitePayBillingProvider()
    except InfinitePayError as exc:
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
        plan_code=subscription.plan_code,
        billing_interval=subscription.billing_interval,
        amount_paid_cents=subscription.amount_paid_cents,
        last_payment_method=subscription.last_payment_method,
        current_period_end=subscription.current_period_end,
        trial_ends_at=subscription.trial_ends_at,
        grace_ends_at=subscription.grace_ends_at,
        trial_days_remaining=math.ceil(trial_seconds / 86400) if trial_active else 0,
        access_allowed=access_allowed,
        management_available=subscription.provider == "stripe" and bool(
            subscription.provider_customer_id and subscription.provider_subscription_id
        ),
        cancel_at_period_end=subscription.cancel_at_period_end,
    )


async def create_infinitepay_checkout(
    payload: BillingCheckoutCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
) -> BillingSessionRead:
    provider = get_infinitepay_provider()
    offer = get_plan_offer(payload.plan, payload.interval)
    subscription = await db.scalar(
        select(Subscription).where(Subscription.tenant_id == tenant.id).with_for_update()
    )
    if not subscription:
        subscription = Subscription(tenant_id=tenant.id, provider="infinitepay")
        db.add(subscription)
        await db.flush()

    now = datetime.now(UTC)
    reusable_order = await db.scalar(
        select(BillingOrder)
        .where(
            BillingOrder.tenant_id == tenant.id,
            BillingOrder.provider == "infinitepay",
            BillingOrder.plan_code == payload.plan,
            BillingOrder.billing_interval == payload.interval,
            BillingOrder.status == "pending",
            BillingOrder.created_at > now - timedelta(hours=24),
        )
        .order_by(BillingOrder.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if reusable_order and reusable_order.checkout_url:
        return BillingSessionRead(url=reusable_order.checkout_url)

    order = reusable_order or BillingOrder(
        tenant_id=tenant.id,
        subscription_id=subscription.id,
        provider="infinitepay",
        plan_code=payload.plan,
        billing_interval=payload.interval,
        amount_cents=offer.amount_cents,
        status="pending",
    )
    if reusable_order is None:
        db.add(order)
        await db.flush()
    subscription.provider = "infinitepay"
    await db.commit()

    try:
        checkout = await provider.create_checkout(
            order_nsu=f"nexus-{order.id}",
            offer=offer,
            customer_name=user.full_name,
            customer_email=user.email,
            redirect_url=f"{settings.frontend_url}/app?checkout=success",
            webhook_url=settings.infinitepay_webhook_url,
        )
    except InfinitePayError as exc:
        order.status = "failed"
        await db.commit()
        raise HTTPException(status_code=502, detail="Não foi possível iniciar o pagamento agora") from exc

    order.checkout_url = checkout.url
    await db.commit()
    return BillingSessionRead(url=checkout.url)


@router.post("/billing/checkout", response_model=BillingSessionRead)
async def create_checkout(
    payload: BillingCheckoutCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: DbSession,
    _csrf: CsrfGuard,
) -> BillingSessionRead:
    if settings.billing_provider == "infinitepay":
        return await create_infinitepay_checkout(payload, tenant, user, db)

    provider = get_stripe_provider()
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
    if settings.billing_provider == "infinitepay":
        raise HTTPException(
            status_code=409,
            detail="A InfinitePay usa renovação manual. Escolha um plano para gerar uma nova cobrança.",
        )
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription or not subscription.provider_customer_id:
        raise HTTPException(status_code=404, detail="Assinatura ainda não possui cliente de cobrança")
    try:
        session = await get_stripe_provider().create_portal(
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


def parse_infinitepay_order_id(order_nsu: object) -> uuid.UUID | None:
    if not isinstance(order_nsu, str) or not order_nsu.startswith("nexus-"):
        return None
    return parse_uuid(order_nsu.removeprefix("nexus-"))


def add_billing_period(value: datetime, interval: str) -> datetime:
    months = 12 if interval == "annual" else 1
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


async def apply_infinitepay_payment(
    db: DbSession,
    *,
    order: BillingOrder,
    transaction_nsu: str,
    invoice_slug: str,
    payment: InfinitePayPayment,
    event_payload: dict,
) -> None:
    if not payment.paid:
        raise HTTPException(status_code=400, detail="Pagamento ainda não foi confirmado")
    if payment.amount_cents != order.amount_cents:
        raise HTTPException(status_code=400, detail="Valor do pagamento não corresponde ao pedido")
    if order.status == "paid":
        if order.provider_transaction_id != transaction_nsu:
            raise HTTPException(status_code=409, detail="Pedido já foi pago por outra transação")
        return

    existing_transaction = await db.scalar(
        select(BillingOrder.id).where(
            BillingOrder.provider_transaction_id == transaction_nsu,
            BillingOrder.id != order.id,
        )
    )
    if existing_transaction:
        raise HTTPException(status_code=409, detail="Transação já vinculada a outro pedido")

    record = WebhookEvent(
        provider="infinitepay",
        external_event_id=transaction_nsu,
        event_type="payment.paid",
        payload=event_payload,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return

    subscription = await db.scalar(
        select(Subscription).where(Subscription.id == order.subscription_id).with_for_update()
    )
    if not subscription or subscription.tenant_id != order.tenant_id:
        raise HTTPException(status_code=400, detail="Assinatura do pedido não encontrada")

    now = datetime.now(UTC)
    old_status = subscription.status
    period_start = (
        subscription.current_period_end
        if subscription.status == SubscriptionStatus.ACTIVE
        and subscription.current_period_end is not None
        and subscription.current_period_end > now
        else now
    )
    subscription.provider = "infinitepay"
    subscription.provider_subscription_id = transaction_nsu
    subscription.plan_code = order.plan_code
    subscription.billing_interval = order.billing_interval
    subscription.amount_paid_cents = order.amount_cents
    subscription.last_payment_method = payment.capture_method
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_end = add_billing_period(period_start, order.billing_interval)
    subscription.grace_ends_at = None
    subscription.cancel_at_period_end = False
    subscription.checkout_attempt_id = None
    subscription.checkout_attempt_created_at = None
    subscription.last_provider_event_created_at = now

    order.status = "paid"
    order.provider_transaction_id = transaction_nsu
    order.provider_invoice_slug = invoice_slug
    order.capture_method = payment.capture_method
    order.installments = payment.installments
    order.paid_at = now
    record.processed = True

    tenant = await db.get(Tenant, order.tenant_id)
    if tenant and (
        old_status != SubscriptionStatus.ACTIVE
        or tenant.status
        in {
            TenantStatus.PENDING_PAYMENT,
            TenantStatus.GRACE_PERIOD,
            TenantStatus.SUSPENDED,
            TenantStatus.CANCELED,
        }
    ):
        tenant.status = TenantStatus.PROVISIONING
        db.add(
            OutboxEvent(
                tenant_id=tenant.id,
                event_type="tenant.provisioning.requested",
                payload={
                    "tenant_id": str(tenant.id),
                    "source": "infinitepay",
                    "plan": order.plan_code,
                    "interval": order.billing_interval,
                },
            )
        )
    await db.commit()


async def verify_infinitepay_order(
    db: DbSession,
    *,
    order_nsu: str,
    transaction_nsu: str,
    invoice_slug: str,
    event_payload: dict,
    tenant_id: uuid.UUID | None = None,
) -> None:
    order_id = parse_infinitepay_order_id(order_nsu)
    if not order_id:
        raise HTTPException(status_code=400, detail="Pedido inválido")
    order = await db.scalar(select(BillingOrder).where(BillingOrder.id == order_id).with_for_update())
    if not order or order.provider != "infinitepay":
        raise HTTPException(status_code=400, detail="Pedido não encontrado")
    if tenant_id is not None and order.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Pedido não pertence a esta conta")
    if order.status == "paid" and order.provider_transaction_id == transaction_nsu:
        return

    try:
        payment = await get_infinitepay_provider().verify_payment(
            order_nsu=order_nsu,
            transaction_nsu=transaction_nsu,
            slug=invoice_slug,
        )
    except InfinitePayError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível confirmar o pagamento agora") from exc
    await apply_infinitepay_payment(
        db,
        order=order,
        transaction_nsu=transaction_nsu,
        invoice_slug=invoice_slug,
        payment=payment,
        event_payload=event_payload,
    )


@router.post("/billing/infinitepay/verify")
async def verify_infinitepay_redirect(
    payload: InfinitePayVerificationRequest,
    tenant: CurrentTenant,
    db: DbSession,
    _csrf: CsrfGuard,
) -> dict[str, bool]:
    event_payload = payload.model_dump()
    await verify_infinitepay_order(
        db,
        order_nsu=payload.order_nsu,
        transaction_nsu=payload.transaction_nsu,
        invoice_slug=payload.slug,
        event_payload=event_payload,
        tenant_id=tenant.id,
    )
    return {"verified": True}


@router.post("/webhooks/infinitepay", include_in_schema=False)
async def infinitepay_webhook(request: Request, db: DbSession) -> dict[str, bool]:
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Webhook inválido") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook inválido")
    order_nsu = payload.get("order_nsu")
    transaction_nsu = payload.get("transaction_nsu")
    invoice_slug = payload.get("invoice_slug")
    if not all(isinstance(value, str) and value for value in (order_nsu, transaction_nsu, invoice_slug)):
        raise HTTPException(status_code=400, detail="Webhook incompleto")
    await verify_infinitepay_order(
        db,
        order_nsu=order_nsu,
        transaction_nsu=transaction_nsu,
        invoice_slug=invoice_slug,
        event_payload=payload,
    )
    return {"success": True}


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
