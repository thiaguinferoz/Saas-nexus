import unittest
import uuid
from datetime import UTC, datetime

import jwt
from fastapi import HTTPException

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.dependencies import get_current_user  # noqa: E402
from app.models import User  # noqa: E402
from app.security import create_access_token, decode_access_token, settings  # noqa: E402


class FakeUserSession:
    def __init__(self, user: User) -> None:
        self.user = user

    async def get(self, model, key):
        return self.user if model is User and key == self.user.id else None


class AccessTokenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.user_id = uuid.uuid4()

    def test_token_round_trip_preserves_session_version(self) -> None:
        token = create_access_token(self.user_id, 7)

        decoded_user_id, decoded_version = decode_access_token(token)

        self.assertEqual(decoded_user_id, self.user_id)
        self.assertEqual(decoded_version, 7)

    def test_legacy_token_without_session_version_is_rejected(self) -> None:
        token = jwt.encode(
            {
                "sub": str(self.user_id),
                "type": "access",
                "exp": datetime(2099, 1, 1, tzinfo=UTC),
            },
            settings.app_secret_key,
            algorithm="HS256",
        )

        with self.assertRaises(jwt.InvalidTokenError):
            decode_access_token(token)

    async def test_changed_session_version_revokes_existing_token(self) -> None:
        token = create_access_token(self.user_id, 3)
        user = User(
            id=self.user_id,
            email="owner@example.com",
            password_hash="not-used",
            full_name="Owner",
            is_active=True,
            session_version=4,
            email_verified_at=datetime.now(UTC),
        )

        with self.assertRaises(HTTPException) as context:
            await get_current_user(FakeUserSession(user), token)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Sessão revogada")

    async def test_matching_session_version_keeps_verified_user_authenticated(self) -> None:
        token = create_access_token(self.user_id, 4)
        user = User(
            id=self.user_id,
            email="owner@example.com",
            password_hash="not-used",
            full_name="Owner",
            is_active=True,
            session_version=4,
            email_verified_at=datetime.now(UTC),
        )

        current_user = await get_current_user(FakeUserSession(user), token)

        self.assertIs(current_user, user)
