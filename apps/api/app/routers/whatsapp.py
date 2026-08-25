import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.billing.access import sync_billing_access
from app.config import get_settings
from app.dependencies import CsrfGuard, CurrentTenant, DbSession
from app.models import OutboundMessage, OutboundMessageStatus, OutboxEvent, Subscription, SubscriptionStatus, Tenant, TenantSettings, TenantStatus, WebhookEvent, WhatsAppConnection, WhatsAppConnectionStatus, WorkflowExecution
from app.schemas import WhatsAppConnectionRead, WhatsAppOnboardingComplete, WhatsAppOnboardingSessionRead
from app.ycloud.client import YCloudClient

router = APIRouter(tags=["whatsapp"])
settings = get_settings()


@router.get("/whatsapp/connection", response_model=WhatsAppConnectionRead | None)
async def read_connection(tenant: CurrentTenant, db: DbSession) -> WhatsAppConnectionRead | None:
    connection = await db.scalar(select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == tenant.id))
    return WhatsAppConnectionRead.model_validate(connection) if connection else None


@router.post("/whatsapp/onboarding/session", response_model=WhatsAppOnboardingSessionRead)
async def create_onboarding_session(tenant: CurrentTenant, db: DbSession, _csrf: CsrfGuard) -> WhatsAppOnboardingSessionRead:
    if not settings.meta_app_id or not settings.meta_embedded_signup_config_id or not settings.ycloud_solution_id:
        raise HTTPException(status_code=503, detail="Embedded Signup ainda não configurado")
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not subscription or subscription.status not in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
        raise HTTPException(status_code=402, detail="É necessário ativar a assinatura antes de conectar o WhatsApp")
    now = datetime.now(UTC)
    state = jwt.encode({"sub": str(tenant.id), "type": "ycloud_onboarding", "iat": now, "exp": now + timedelta(minutes=15)}, settings.app_secret_key, algorithm="HS256")
    return WhatsAppOnboardingSessionRead(
        app_id=settings.meta_app_id,
        configuration_id=settings.meta_embedded_signup_config_id,
        solution_id=settings.ycloud_solution_id,
        state=state,
    )


@router.post("/whatsapp/onboarding/complete", response_model=WhatsAppConnectionRead)
async def complete_onboarding(payload: WhatsAppOnboardingComplete, tenant: CurrentTenant, db: DbSession, _csrf: CsrfGuard) -> WhatsAppConnectionRead:
    try:
        claims = jwt.decode(payload.state, settings.app_secret_key, algorithms=["HS256"])
        if claims.get("type") != "ycloud_onboarding" or claims.get("sub") != str(tenant.id):
            raise ValueError
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=400, detail="Sessão de conexão inválida ou expirada") from None
    try:
        remote = await YCloudClient().bind_coexistence_waba(waba_id=payload.waba_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="A YCloud não conseguiu vincular esta conta em modo de coexistência") from exc
    remote_phone = str(remote.get("phoneNumber") or payload.phone_number)
    remote_digits = "".join(character for character in remote_phone if character.isdigit())
    canonical_phone = f"+{remote_digits}" if remote_digits else payload.phone_number
    remote_phone_number_id = str(remote.get("id") or payload.phone_number_id or "") or None
    connection = await db.scalar(select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == tenant.id))
    if not connection:
        connection = WhatsAppConnection(tenant_id=tenant.id, waba_id=payload.waba_id, phone_number=canonical_phone)
        db.add(connection)
    connection.waba_id = payload.waba_id
    connection.phone_number = canonical_phone
    connection.phone_number_id = remote_phone_number_id
    connection.display_name = remote.get("verifiedName") or remote.get("displayName")
    connection.quality_rating = remote.get("qualityRating")
    connection.status = WhatsAppConnectionStatus.CONNECTED
    tenant.status = TenantStatus.ACTIVE
    db.add(OutboxEvent(tenant_id=tenant.id, event_type="whatsapp.connection.activated", payload={"tenant_id": str(tenant.id), "waba_id": payload.waba_id, "phone_number": canonical_phone, "phone_number_id": remote_phone_number_id, "mode": "coexistence"}))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Este número já está conectado a outra empresa") from None
    await db.refresh(connection)
    return WhatsAppConnectionRead.model_validate(connection)


def verify_signature(raw_body: bytes, signature_header: str | None) -> None:
    if not settings.ycloud_webhook_secret or not signature_header:
        raise HTTPException(status_code=401, detail="Assinatura ausente")
    parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
    timestamp = parts.get("t")
    received = parts.get("s")
    if not timestamp or not received:
        raise HTTPException(status_code=401, detail="Assinatura inválida")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=401, detail="Webhook expirado")
    except ValueError:
        raise HTTPException(status_code=401, detail="Timestamp inválido") from None
    signed = timestamp.encode() + b"." + raw_body
    expected = hmac.new(settings.ycloud_webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Assinatura inválida")


@router.post("/webhooks/ycloud", include_in_schema=False)
async def ycloud_webhook(request: Request, db: DbSession) -> dict[str, bool]:
    raw_body = await request.body()
    verify_signature(raw_body, request.headers.get("ycloud-signature"))
    try:
        event = json.loads(raw_body)
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Payload YCloud inválido") from None
    record = WebhookEvent(provider="ycloud", external_event_id=event["id"], event_type=event["type"], payload=event)
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"received": True}
    content = event.get("whatsappInboundMessage") or event.get("whatsappMessage") or event.get("whatsappPhoneNumber") or {}
    waba_id = content.get("wabaId")
    phone = content.get("to") or content.get("phoneNumber") or content.get("from")
    connection = None
    if waba_id or phone:
        connection = await db.scalar(select(WhatsAppConnection).where(or_(WhatsAppConnection.waba_id == waba_id, WhatsAppConnection.phone_number == phone)))
    if connection and event["type"] in {"whatsapp.inbound_message.received", "whatsapp.smb.message.echoes"}:
        current_settings = await db.scalar(select(TenantSettings).where(TenantSettings.tenant_id == connection.tenant_id, TenantSettings.is_active.is_(True)).order_by(TenantSettings.version.desc()).limit(1))
        tenant = await db.get(Tenant, connection.tenant_id)
        billing_allowed = False
        if tenant:
            _, billing_allowed = await sync_billing_access(db, tenant)
        if current_settings and tenant and billing_allowed and tenant.status in {TenantStatus.ACTIVE, TenantStatus.GRACE_PERIOD}:
            execution = WorkflowExecution(tenant_id=connection.tenant_id, webhook_event_id=record.id, provider_event_id=event["id"], config_version=current_settings.version, schema_version=settings.workflow_schema_version)
            db.add(execution)
            await db.flush()
            db.add(OutboxEvent(tenant_id=connection.tenant_id, event_type="whatsapp.inbound.received", payload={"tenant_id": str(connection.tenant_id), "ycloud_event_id": event["id"], "execution_id": str(execution.id), "correlation_id": str(execution.correlation_id), "schema_version": execution.schema_version}))
    elif event["type"] == "whatsapp.message.updated":
        external_id = content.get("externalId")
        if external_id:
            outbound = await db.scalar(select(OutboundMessage).where(OutboundMessage.idempotency_key == external_id))
            if outbound:
                provider_status = str(content.get("status") or "").lower()
                status_map = {"sent": OutboundMessageStatus.SENT, "delivered": OutboundMessageStatus.DELIVERED, "read": OutboundMessageStatus.READ, "failed": OutboundMessageStatus.FAILED}
                if provider_status in status_map:
                    outbound.status = status_map[provider_status]
                    if outbound.status in {OutboundMessageStatus.SENT, OutboundMessageStatus.DELIVERED, OutboundMessageStatus.READ} and not outbound.sent_at:
                        outbound.sent_at = datetime.now(UTC)
                outbound.provider_message_id = content.get("id") or content.get("wamid") or outbound.provider_message_id
    elif connection and event["type"] == "whatsapp.phone_number.deleted":
        connection.status = WhatsAppConnectionStatus.DISCONNECTED
    record.processed = True
    await db.commit()
    return {"received": True}
