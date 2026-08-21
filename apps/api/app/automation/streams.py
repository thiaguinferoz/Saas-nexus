import json
from collections.abc import Mapping

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import get_settings

settings = get_settings()


def redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, health_check_interval=30)


def stream_name(channel: str) -> str:
    return f"{settings.redis_stream_prefix}:{channel}"


def stream_for_event(event_type: str) -> str:
    if event_type == "whatsapp.inbound.received":
        return stream_name("automation")
    if event_type == "whatsapp.message.send.requested":
        return stream_name("outbound")
    if event_type == "support.ticket.created":
        return stream_name("support")
    return stream_name("provisioning")


async def ensure_group(redis: Redis, stream: str, group: str) -> None:
    try:
        await redis.xgroup_create(stream, group, id="0-0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def encode_event(*, outbox_event_id: str, tenant_id: str, event_type: str, payload: dict) -> dict[str, str]:
    return {"outbox_event_id": outbox_event_id, "tenant_id": tenant_id, "event_type": event_type, "payload": json.dumps(payload, separators=(",", ":"), ensure_ascii=False)}


def decode_payload(fields: Mapping[str, str]) -> dict:
    return json.loads(fields.get("payload", "{}"))
