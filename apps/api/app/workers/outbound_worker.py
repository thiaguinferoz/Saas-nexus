import asyncio
import socket
import uuid

import httpx
from sqlalchemy import select

from app.automation.streams import decode_payload, ensure_group, redis_client, stream_name
from app.config import get_settings
from app.database import SessionLocal
from app.models import OutboundMessage, OutboundMessageStatus, WhatsAppConnection
from app.ycloud.client import YCloudClient

settings = get_settings()
STREAM = stream_name("outbound")
GROUP = "ycloud-senders"
CONSUMER = f"sender-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def process(redis, redis_id: str, fields: dict[str, str]) -> None:
    payload = decode_payload(fields)
    message_id = uuid.UUID(payload["message_id"])
    async with SessionLocal() as db:
        message = await db.get(OutboundMessage, message_id, with_for_update=True)
        if not message or message.status in {OutboundMessageStatus.SUBMITTED, OutboundMessageStatus.SENT, OutboundMessageStatus.DELIVERED, OutboundMessageStatus.READ}:
            await redis.xack(STREAM, GROUP, redis_id)
            return
        if message.status == OutboundMessageStatus.SENDING:
            message.status = OutboundMessageStatus.DEAD_LETTER
            message.last_error = "Envio anterior ficou sem confirmação; requer reconciliação para evitar duplicidade"
            await db.commit()
            await redis.xadd(stream_name("dlq"), {**fields, "failed_stream": STREAM, "failed_id": redis_id, "error": message.last_error}, maxlen=10000, approximate=True)
            await redis.xack(STREAM, GROUP, redis_id)
            return
        connection = await db.scalar(select(WhatsAppConnection).where(WhatsAppConnection.tenant_id == message.tenant_id))
        if not connection:
            message.status = OutboundMessageStatus.DEAD_LETTER
            message.last_error = "Conexão WhatsApp não encontrada"
            await db.commit()
            await redis.xack(STREAM, GROUP, redis_id)
            return
        message.attempts += 1
        message.status = OutboundMessageStatus.SENDING
        await db.commit()
        try:
            result = await YCloudClient().send_text(sender=connection.phone_number, to=message.recipient, recipient_id=message.recipient_id, text=message.payload["text"], reply_to_message_id=message.payload.get("reply_to_message_id"), external_id=message.idempotency_key)
        except Exception as exc:
            message = await db.get(OutboundMessage, message_id, with_for_update=True)
            if not message:
                await redis.xack(STREAM, GROUP, redis_id)
                return
            message.last_error = f"{type(exc).__name__}: {str(exc)[:1000]}"
            ambiguous = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))
            if ambiguous or message.attempts >= settings.worker_max_attempts:
                message.status = OutboundMessageStatus.DEAD_LETTER
                await redis.xadd(stream_name("dlq"), {**fields, "failed_stream": STREAM, "failed_id": redis_id, "error": message.last_error}, maxlen=10000, approximate=True)
                await redis.xack(STREAM, GROUP, redis_id)
            else:
                message.status = OutboundMessageStatus.FAILED
            await db.commit()
            return
        message = await db.get(OutboundMessage, message_id, with_for_update=True)
        if message:
            message.status = OutboundMessageStatus.SUBMITTED
            message.provider_message_id = result.get("id") or result.get("messageId")
            message.last_error = None
            await db.commit()
        await redis.xack(STREAM, GROUP, redis_id)


async def next_messages(redis) -> list[tuple[str, dict[str, str]]]:
    response = await redis.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=10, block=settings.worker_block_ms)
    if response:
        return response[0][1]
    claimed = await redis.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=settings.worker_claim_idle_ms, start_id="0-0", count=10)
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
