import asyncio
import socket
import uuid
from datetime import UTC, datetime

from app.automation.streams import decode_payload, ensure_group, redis_client, stream_name
from app.config import get_settings
from app.database import SessionLocal
from app.email import EmailDeliveryError, TransactionalEmailService
from app.models import SupportTicket, Tenant, User

settings = get_settings()
STREAM = stream_name("support")
GROUP = "support-emailers"
CONSUMER = f"support-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def move_to_dlq(redis, redis_id: str, fields: dict[str, str], error: str) -> None:
    await redis.xadd(
        stream_name("dlq"),
        {**fields, "failed_stream": STREAM, "failed_id": redis_id, "error": error},
        maxlen=10000,
        approximate=True,
    )
    await redis.xack(STREAM, GROUP, redis_id)


async def process(redis, redis_id: str, fields: dict[str, str]) -> None:
    try:
        ticket_id = uuid.UUID(decode_payload(fields)["ticket_id"])
    except (KeyError, TypeError, ValueError) as exc:
        await move_to_dlq(redis, redis_id, fields, f"Payload inválido: {type(exc).__name__}")
        return

    async with SessionLocal() as db:
        ticket = await db.get(SupportTicket, ticket_id, with_for_update=True)
        if not ticket:
            await move_to_dlq(redis, redis_id, fields, "Ticket não encontrado")
            return
        if ticket.notification_sent_at:
            await redis.xack(STREAM, GROUP, redis_id)
            return

        user = await db.get(User, ticket.created_by)
        tenant = await db.get(Tenant, ticket.tenant_id)
        if not user or not tenant:
            await move_to_dlq(redis, redis_id, fields, "Solicitante ou tenant não encontrado")
            return

        ticket.notification_attempts += 1
        await db.commit()

        try:
            if not settings.support_email:
                raise EmailDeliveryError("Destino de suporte ainda não configurado")
            await TransactionalEmailService().send_support_ticket(
                to=settings.support_email,
                requester_email=user.email,
                requester_name=user.full_name,
                company_name=tenant.name,
                ticket_id=ticket.id,
                category=ticket.category.value,
                priority=ticket.priority.value,
                subject=ticket.subject,
                message=ticket.message,
                preferred_channel=ticket.preferred_channel,
                contact_value=ticket.contact_value,
            )
        except Exception as exc:
            ticket = await db.get(SupportTicket, ticket_id, with_for_update=True)
            if not ticket:
                await move_to_dlq(redis, redis_id, fields, "Ticket removido durante a notificação")
                return
            if isinstance(exc, EmailDeliveryError):
                error = str(exc)[:500]
            else:
                error = f"Falha inesperada no envio ({type(exc).__name__})"
            ticket.notification_last_error = error
            exhausted = ticket.notification_attempts >= settings.worker_max_attempts
            await db.commit()
            if exhausted:
                await move_to_dlq(redis, redis_id, fields, error)
            return

        ticket = await db.get(SupportTicket, ticket_id, with_for_update=True)
        if not ticket:
            await move_to_dlq(redis, redis_id, fields, "Ticket removido após a notificação")
            return
        ticket.notification_sent_at = datetime.now(UTC)
        ticket.notification_last_error = None
        await db.commit()
        await redis.xack(STREAM, GROUP, redis_id)


async def next_messages(redis) -> list[tuple[str, dict[str, str]]]:
    response = await redis.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=10, block=settings.worker_block_ms)
    if response:
        return response[0][1]
    claimed = await redis.xautoclaim(
        STREAM,
        GROUP,
        CONSUMER,
        min_idle_time=settings.worker_claim_idle_ms,
        start_id="0-0",
        count=10,
    )
    return claimed[1] if len(claimed) > 1 else []


async def main() -> None:
    redis = redis_client()
    await ensure_group(redis, STREAM, GROUP)
    try:
        while True:
            for redis_id, fields in await next_messages(redis):
                await process(redis, redis_id, fields)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
