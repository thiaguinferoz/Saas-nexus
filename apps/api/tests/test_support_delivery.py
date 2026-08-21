import json
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.automation.streams import stream_for_event, stream_name  # noqa: E402
from app.models import (  # noqa: E402
    SupportTicket,
    SupportTicketCategory,
    SupportTicketPriority,
    SupportTicketStatus,
    Tenant,
    TenantStatus,
    User,
)
from app.workers.support_worker import process  # noqa: E402


class FakeRedis:
    def __init__(self) -> None:
        self.acked = []
        self.dead_letters = []

    async def xack(self, stream, group, redis_id):
        self.acked.append((stream, group, redis_id))

    async def xadd(self, stream, fields, **_kwargs):
        self.dead_letters.append((stream, fields))


class FakeSupportDb:
    def __init__(self, ticket: SupportTicket, user: User, tenant: Tenant) -> None:
        self.ticket = ticket
        self.user = user
        self.tenant = tenant
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, model, key, **_kwargs):
        if model is SupportTicket and key == self.ticket.id:
            return self.ticket
        if model is User and key == self.user.id:
            return self.user
        if model is Tenant and key == self.tenant.id:
            return self.tenant
        return None

    async def commit(self) -> None:
        self.commit_count += 1


class FakeEmailService:
    sent = []

    async def send_support_ticket(self, **kwargs) -> None:
        self.sent.append(kwargs)


class SupportDeliveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeEmailService.sent = []
        self.tenant = Tenant(
            id=uuid.uuid4(),
            name="Acme",
            slug=f"acme-{uuid.uuid4().hex}",
            status=TenantStatus.ACTIVE,
        )
        self.user = User(
            id=uuid.uuid4(),
            email="owner@example.com",
            password_hash="not-used",
            full_name="Owner",
            is_active=True,
            session_version=0,
            email_verified_at=datetime.now(UTC),
        )
        self.ticket = SupportTicket(
            id=uuid.uuid4(),
            tenant_id=self.tenant.id,
            created_by=self.user.id,
            category=SupportTicketCategory.SUPPORT,
            priority=SupportTicketPriority.NORMAL,
            status=SupportTicketStatus.OPEN,
            subject="Preciso de ajuda",
            message="Mensagem do cliente",
            preferred_channel="platform",
            contact_value=None,
            notification_attempts=0,
            notification_sent_at=None,
            notification_last_error=None,
        )

    def test_support_event_routes_to_dedicated_stream(self) -> None:
        self.assertEqual(stream_for_event("support.ticket.created"), stream_name("support"))
        self.assertNotEqual(stream_for_event("support.ticket.created"), stream_name("provisioning"))

    async def test_worker_sends_notification_once_and_acknowledges_message(self) -> None:
        redis = FakeRedis()
        db = FakeSupportDb(self.ticket, self.user, self.tenant)
        fields = {"payload": json.dumps({"ticket_id": str(self.ticket.id)})}

        with (
            patch("app.workers.support_worker.SessionLocal", return_value=db),
            patch("app.workers.support_worker.TransactionalEmailService", FakeEmailService),
            patch("app.workers.support_worker.settings.support_email", "support@example.com"),
        ):
            await process(redis, "1-0", fields)

        self.assertEqual(self.ticket.notification_attempts, 1)
        self.assertIsNotNone(self.ticket.notification_sent_at)
        self.assertIsNone(self.ticket.notification_last_error)
        self.assertEqual(len(FakeEmailService.sent), 1)
        self.assertEqual(FakeEmailService.sent[0]["to"], "support@example.com")
        self.assertEqual(FakeEmailService.sent[0]["ticket_id"], self.ticket.id)
        self.assertEqual(len(redis.acked), 1)
        self.assertEqual(redis.dead_letters, [])

    async def test_worker_skips_already_notified_ticket_without_duplicate_email(self) -> None:
        self.ticket.notification_sent_at = datetime.now(UTC)
        redis = FakeRedis()
        db = FakeSupportDb(self.ticket, self.user, self.tenant)
        fields = {"payload": json.dumps({"ticket_id": str(self.ticket.id)})}

        with (
            patch("app.workers.support_worker.SessionLocal", return_value=db),
            patch("app.workers.support_worker.TransactionalEmailService", FakeEmailService),
        ):
            await process(redis, "2-0", fields)

        self.assertEqual(FakeEmailService.sent, [])
        self.assertEqual(len(redis.acked), 1)

    async def test_worker_moves_invalid_payload_to_dead_letter_queue(self) -> None:
        redis = FakeRedis()

        await process(redis, "3-0", {"payload": "{}"})

        self.assertEqual(len(redis.dead_letters), 1)
        dead_letter_stream, dead_letter = redis.dead_letters[0]
        self.assertEqual(dead_letter_stream, stream_name("dlq"))
        self.assertEqual(dead_letter["failed_id"], "3-0")
        self.assertIn("Payload inválido", dead_letter["error"])
        self.assertEqual(len(redis.acked), 1)
