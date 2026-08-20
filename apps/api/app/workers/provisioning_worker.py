import asyncio
import socket
import uuid

from sqlalchemy import select

from app.automation.streams import decode_payload, ensure_group, redis_client, stream_name
from app.config import get_settings
from app.database import SessionLocal
from app.models import Subscription, SubscriptionStatus, Tenant, TenantStatus

settings = get_settings()
STREAM = stream_name("provisioning")
GROUP = "tenant-provisioners"
CONSUMER = f"provisioning-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def process(redis, redis_id: str, fields: dict[str, str]) -> None:
    event_type = fields.get("event_type", "")
    payload = decode_payload(fields)
    if event_type != "tenant.provisioning.requested":
        await redis.xack(STREAM, GROUP, redis_id)
        return
    tenant_id = uuid.UUID(payload.get("tenant_id") or fields["tenant_id"])
    async with SessionLocal() as db:
        tenant = await db.get(Tenant, tenant_id, with_for_update=True)
        subscription = None
        if tenant:
            subscription = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
        if not tenant or not subscription:
            await redis.xadd(stream_name("dlq"), {**fields, "failed_stream": STREAM, "failed_id": redis_id, "error": "Tenant ou assinatura não encontrados"}, maxlen=10000, approximate=True)
            await redis.xack(STREAM, GROUP, redis_id)
            return
        if subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING} and tenant.status == TenantStatus.PROVISIONING:
            tenant.status = TenantStatus.AWAITING_WHATSAPP
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
