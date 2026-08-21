import unittest
from unittest.mock import patch

import httpx

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.email import EmailDeliveryError, TransactionalEmailService  # noqa: E402


class FailingHttpClient:
    def __init__(self, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *_args, **_kwargs):
        request = httpx.Request("POST", "https://api.resend.com/emails")
        raise httpx.ConnectError(
            "upstream leaked Authorization: Bearer re_sensitive_value",
            request=request,
        )


class TransactionalEmailTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_error_becomes_generic_delivery_error_without_sensitive_details(self) -> None:
        service = TransactionalEmailService()

        with (
            patch("app.email.httpx.AsyncClient", FailingHttpClient),
            self.assertRaises(EmailDeliveryError) as context,
        ):
            await service.send(
                to="recipient@example.com",
                subject="Assunto",
                html_body="<p>Conteúdo</p>",
                idempotency_key="email-test-1",
            )

        message = str(context.exception)
        self.assertEqual(message, "Não foi possível conectar ao serviço de e-mail agora")
        self.assertNotIn("re_sensitive_value", message)
        self.assertNotIn("Authorization", message)
        self.assertIsInstance(context.exception.__cause__, httpx.HTTPError)
