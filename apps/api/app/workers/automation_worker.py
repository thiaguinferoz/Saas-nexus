import asyncio
import socket
import uuid
from datetime import UTC, datetime

import httpx

from app.automation.streams import decode_payload, ensure_group, redis_client, stream_name
from app.config import get_settings
from app.database import SessionLocal
from app.models import WorkflowExecution, WorkflowExecutionStatus

settings = get_settings()
STREAM = stream_name("automation")
GROUP = "n8n-dispatchers"
CONSUMER = f"automation-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def invoke_n8n(execution: WorkflowExecution) -> None:
    headers = {settings.n8n_webhook_header_name: settings.n8n_service_token or ""}
    payload = {"schema_version": execution.schema_version, "execution_id": str(execution.id), "tenant_id": str(execution.tenant_id), "correlation_id": str(execution.correlation_id)}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(settings.n8n_internal_webhook_url, headers=headers, json=payload)
        response.raise_for_status()


async def process(redis, redis_id: str, fields: dict[str, str]) -> None:
    payload = decode_payload(fields)
    execution_id = uuid.UUID(payload["execution_id"])
    async with SessionLocal() as db:
        execution = await db.get(WorkflowExecution, execution_id, with_for_update=True)
        if not execution or execution.status in {WorkflowExecutionStatus.RUNNING, WorkflowExecutionStatus.SUCCEEDED}:
            await redis.xack(STREAM, GROUP, redis_id)
            return
        execution.attempts += 1
        execution.status = WorkflowExecutionStatus.DISPATCHING
        execution.started_at = execution.started_at or datetime.now(UTC)
        await db.commit()
        try:
            await invoke_n8n(execution)
        except Exception as exc:
            execution = await db.get(WorkflowExecution, execution_id, with_for_update=True)
            if not execution:
                await redis.xack(STREAM, GROUP, redis_id)
                return
            execution.last_error = f"{type(exc).__name__}: {str(exc)[:1000]}"
            if execution.attempts >= settings.worker_max_attempts:
                execution.status = WorkflowExecutionStatus.DEAD_LETTER
                execution.completed_at = datetime.now(UTC)
                await redis.xadd(stream_name("dlq"), {**fields, "failed_stream": STREAM, "failed_id": redis_id, "error": execution.last_error}, maxlen=10000, approximate=True)
                await redis.xack(STREAM, GROUP, redis_id)
            else:
                execution.status = WorkflowExecutionStatus.RETRYING
            await db.commit()
            return
        execution = await db.get(WorkflowExecution, execution_id, with_for_update=True)
        if execution:
            execution.status = WorkflowExecutionStatus.RUNNING
            execution.last_error = None
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
