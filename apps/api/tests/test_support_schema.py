import unittest

from pydantic import ValidationError

from app.schemas import SupportTicketCreate


class SupportTicketSchemaTests(unittest.TestCase):
    def test_platform_is_the_only_supported_return_channel(self) -> None:
        payload = SupportTicketCreate(
            subject="Erro no painel",
            message="Preciso de ajuda com a configuração.",
        )

        self.assertEqual(payload.preferred_channel, "platform")
        self.assertIsNone(payload.contact_value)

    def test_external_return_channels_are_rejected(self) -> None:
        for channel in ("email", "whatsapp", "phone"):
            with self.subTest(channel=channel), self.assertRaises(ValidationError):
                SupportTicketCreate(
                    subject="Erro no painel",
                    message="Preciso de ajuda com a configuração.",
                    preferred_channel=channel,
                )


if __name__ == "__main__":
    unittest.main()

