import unittest
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.dependencies import is_platform_admin, require_platform_admin  # noqa: E402
from app.models import User  # noqa: E402


def make_user(email: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="not-used",
        full_name="Test User",
        is_active=True,
        session_version=0,
        email_verified_at=datetime.now(UTC),
    )


class PlatformAdminAccessTests(unittest.IsolatedAsyncioTestCase):
    def test_configured_email_is_platform_admin_case_insensitively(self) -> None:
        self.assertTrue(is_platform_admin(make_user("Admin@Example.com")))

    def test_customer_is_not_platform_admin(self) -> None:
        self.assertFalse(is_platform_admin(make_user("customer@example.com")))

    async def test_dependency_rejects_customer(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await require_platform_admin(make_user("customer@example.com"))

        self.assertEqual(context.exception.status_code, 403)

    async def test_dependency_accepts_configured_admin(self) -> None:
        user = make_user("operations@example.com")

        current = await require_platform_admin(user)

        self.assertIs(current, user)
