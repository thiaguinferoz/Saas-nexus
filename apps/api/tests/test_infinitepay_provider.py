import json
import unittest

import httpx

from tests._bootstrap import configure_test_environment

configure_test_environment()

from app.billing.infinitepay_provider import (  # noqa: E402
    InfinitePayBillingProvider,
    InfinitePayError,
    get_plan_offer,
)


class InfinitePayProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkout_uses_server_price_and_expected_payload(self) -> None:
        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"url": "https://checkout.infinitepay.com.br/nexus"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = InfinitePayBillingProvider(client)
            checkout = await provider.create_checkout(
                order_nsu="nexus-123",
                offer=get_plan_offer("common", "annual"),
                customer_name="Cliente Nexus",
                customer_email="cliente@example.com",
                redirect_url="https://app.example.com/app?checkout=success",
                webhook_url="https://api.example.com/v1/webhooks/infinitepay",
            )

        self.assertEqual(checkout.url, "https://checkout.infinitepay.com.br/nexus")
        self.assertEqual(captured["handle"], "caio-alves-g6m")
        self.assertEqual(captured["items"][0]["price"], 540_000)
        self.assertEqual(captured["order_nsu"], "nexus-123")
        self.assertEqual(captured["customer"]["email"], "cliente@example.com")

    async def test_payment_check_parses_confirmed_payment(self) -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "paid": True,
                    "amount": 900_000,
                    "paid_amount": 900_000,
                    "installments": 12,
                    "capture_method": "credit_card",
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            payment = await InfinitePayBillingProvider(client).verify_payment(
                order_nsu="nexus-123",
                transaction_nsu="transaction-123",
                slug="invoice-123",
            )

        self.assertTrue(payment.paid)
        self.assertEqual(payment.amount_cents, 900_000)
        self.assertEqual(payment.installments, 12)
        self.assertEqual(payment.capture_method, "credit_card")

    async def test_checkout_rejects_insecure_url(self) -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"url": "http://checkout.invalid/unsafe"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(InfinitePayError):
                await InfinitePayBillingProvider(client).create_checkout(
                    order_nsu="nexus-123",
                    offer=get_plan_offer("common", "monthly"),
                    customer_name="Cliente Nexus",
                    customer_email="cliente@example.com",
                    redirect_url="https://app.example.com/app?checkout=success",
                    webhook_url="https://api.example.com/v1/webhooks/infinitepay",
                )

    def test_catalog_contains_confirmed_prices(self) -> None:
        self.assertEqual(get_plan_offer("common", "monthly").amount_cents, 60_000)
        self.assertEqual(get_plan_offer("common", "annual").amount_cents, 540_000)
        self.assertEqual(get_plan_offer("custom", "monthly").amount_cents, 100_000)
        self.assertEqual(get_plan_offer("custom", "annual").amount_cents, 900_000)
