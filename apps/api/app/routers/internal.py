import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.dependencies import DbSession
from app.models import (
    OutboundMessage,
    OutboxEvent,
    Subscription,
    Tenant,
    TenantSettings,
    TenantStatus,
    WebhookEvent,
    WhatsAppConnection,
    WhatsAppConnectionStatus,
    WorkflowExecution,
    WorkflowExecutionStatus,
)
from app.schemas import OutboundMessageRead, SendTextMessageRequest, TypingIndicatorRequest, WorkflowResultRequest
from app.ycloud.client import YCloudClient

router = APIRouter(prefix="/internal/v1", tags=["internal"])
app_settings = get_settings()


def require_service_token(x_service_token: str = Header(alias="X-Service-Token")) -> None:
    expected = app_settings.n8n_service_token
    if not expected:
        raise HTTPException(status_code=503, detail="Integração interna não configurada")
    if not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(status_code=401, detail="Credencial de serviço inválida")


async def load_execution(execution_id: uuid.UUID, db: DbSession) -> WorkflowExecution:
    execution = await db.get(WorkflowExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


@router.get("/tenants/{tenant_id}/context")
async def read_tenant_context(tenant_id: uuid.UUID, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> dict:
    require_service_token(x_service_token)
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    current = await db.scalar(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id, TenantSettings.is_active.is_(True)).order_by(TenantSettings.version.desc()).limit(1))
    if not current:
        raise HTTPException(status_code=404, detail="Configuração ativa não encontrada")
    return {"tenant_id": str(tenant.id), "tenant_status": tenant.status.value, "config_version": current.version, "settings": current.payload}


@router.get("/executions/{execution_id}/context")
async def read_execution_context(execution_id: uuid.UUID, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> dict:
    require_service_token(x_service_token)
    execution = await load_execution(execution_id, db)
    tenant = await db.get(Tenant, execution.tenant_id)
    if not tenant or tenant.status not in {TenantStatus.ACTIVE, TenantStatus.GRACE_PERIOD}:
        raise HTTPException(status_code=403, detail="Tenant sem permissão para executar automações")
    tenant_settings = await db.scalar(select(TenantSettings).where(TenantSettings.tenant_id == execution.tenant_id, TenantSettings.version == execution.config_version))
    event = await db.get(WebhookEvent, execution.webhook_event_id)
    connection = await db.scalar(select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == execution.tenant_id))
    subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == execution.tenant_id))
    if not tenant_settings or not event or not connection:
        raise HTTPException(status_code=409, detail="Snapshot da execução incompleto")
    return {
        "schema_version": execution.schema_version,
        "execution_id": str(execution.id),
        "correlation_id": str(execution.correlation_id),
        "tenant_id": str(execution.tenant_id),
        "tenant_status": tenant.status.value,
        "config_version": execution.config_version,
        "settings": tenant_settings.payload,
        "subscription_status": subscription.status.value if subscription else "pending",
        "connection": {"sender": connection.phone_number, "waba_id": connection.waba_id, "phone_number_id": connection.phone_number_id},
        "body": event.payload,
    }


@router.post("/executions/{execution_id}/result")
async def record_execution_result(execution_id: uuid.UUID, payload: WorkflowResultRequest, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> dict:
    require_service_token(x_service_token)
    execution = await load_execution(execution_id, db)
    if payload.status not in {WorkflowExecutionStatus.RUNNING, WorkflowExecutionStatus.SUCCEEDED, WorkflowExecutionStatus.FAILED}:
        raise HTTPException(status_code=422, detail="Status de callback inválido")
    execution.status = payload.status
    execution.n8n_execution_id = payload.n8n_execution_id or execution.n8n_execution_id
    execution.last_error = payload.error
    if payload.status in {WorkflowExecutionStatus.SUCCEEDED, WorkflowExecutionStatus.FAILED}:
        execution.completed_at = datetime.now(UTC)
    await db.commit()
    return {"received": True, "execution_id": str(execution.id), "status": execution.status.value}


@router.post("/executions/by-n8n/{n8n_execution_id}/result")
async def record_execution_result_by_n8n(n8n_execution_id: str, payload: WorkflowResultRequest, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> dict:
    require_service_token(x_service_token)
    execution = await db.scalar(select(WorkflowExecution).where(WorkflowExecution.n8n_execution_id == n8n_execution_id))
    if not execution:
        raise HTTPException(status_code=404, detail="Execução n8n não correlacionada")
    execution.status = WorkflowExecutionStatus.FAILED
    execution.last_error = payload.error or "Falha reportada pelo workflow de erro do n8n"
    execution.completed_at = datetime.now(UTC)
    await db.commit()
    return {"received": True, "execution_id": str(execution.id), "status": execution.status.value}


@router.post("/messages", response_model=OutboundMessageRead)
async def queue_text_message(payload: SendTextMessageRequest, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> OutboundMessageRead:
    require_service_token(x_service_token)
    existing = await db.scalar(select(OutboundMessage).where(OutboundMessage.idempotency_key == payload.idempotency_key))
    if existing:
        return OutboundMessageRead(id=existing.id, status=existing.status, idempotency_key=existing.idempotency_key)
    execution = await load_execution(payload.execution_id, db)
    connection = await db.scalar(select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == execution.tenant_id, WhatsAppConnection.status == WhatsAppConnectionStatus.CONNECTED))
    if not connection:
        raise HTTPException(status_code=409, detail="WhatsApp do tenant não está conectado")
    message = OutboundMessage(tenant_id=execution.tenant_id, execution_id=execution.id, idempotency_key=payload.idempotency_key, recipient=payload.to, recipient_id=payload.recipient_id, payload={"text": payload.text, "reply_to_message_id": payload.reply_to_message_id})
    db.add(message)
    await db.flush()
    db.add(OutboxEvent(tenant_id=execution.tenant_id, event_type="whatsapp.message.send.requested", payload={"message_id": str(message.id)}))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(OutboundMessage).where(OutboundMessage.idempotency_key == payload.idempotency_key))
        if not existing:
            raise
        return OutboundMessageRead(id=existing.id, status=existing.status, idempotency_key=existing.idempotency_key)
    return OutboundMessageRead(id=message.id, status=message.status, idempotency_key=message.idempotency_key)


@router.post("/typing")
async def start_typing(payload: TypingIndicatorRequest, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> dict:
    require_service_token(x_service_token)
    await load_execution(payload.execution_id, db)
    try:
        await YCloudClient().start_typing(inbound_message_id=payload.inbound_message_id)
    except Exception:
        return {"accepted": False}
    return {"accepted": True}


@router.get("/executions/{execution_id}/media", response_class=Response)
async def download_execution_media(execution_id: uuid.UUID, db: DbSession, x_service_token: str = Header(alias="X-Service-Token")) -> Response:
    require_service_token(x_service_token)
    execution = await load_execution(execution_id, db)
    event = await db.get(WebhookEvent, execution.webhook_event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento da execução não encontrado")
    content = event.payload.get("whatsappInboundMessage") or {}
    media = content.get(content.get("type") or "") or {}
    media_url = media.get("link")
    if not media_url:
        raise HTTPException(status_code=404, detail="Execução não possui mídia disponível")
    try:
        body, content_type = await YCloudClient().download_media(url=media_url)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Falha ao baixar mídia da YCloud") from exc
    return Response(content=body, media_type=content_type, headers={"Cache-Control": "private, no-store"})
