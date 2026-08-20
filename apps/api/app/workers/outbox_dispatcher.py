import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.automation.streams import encode_event, redis_client, stream_for_event
from app.config import get_settings
from app.database import SessionLocal
from app.models import OutboxEvent

settings = get_settings()


async def dispatch_batch() -> int:
    redis = redis_client()
    try:
        async with SessionLocal() as db:
            events = list((await db.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None)).order_by(OutboxEvent.created_at).with_for_update(skip_locked=True).limit(50))).all())
            for event in events:
                await redis.xadd(stream_for_event(event.event_type), encode_event(outbox_event_id=str(event.id), tenant_id=str(event.tenant_id), event_type=event.event_type, payload=event.payload), maxlen=100000, approximate=True)
                event.published_at = datetime.now(UTC)
            await db.commit()
            return len(events)
    finally:
        await redis.aclose()


async def main() -> None:
    while True:
        try:
            count = await dispatch_batch()
        except Exception as exc:
            print(f"outbox_dispatch_failed error={type(exc).__name__}", flush=True)
            count = 0
        await asyncio.sleep(0 if count else settings.outbox_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
