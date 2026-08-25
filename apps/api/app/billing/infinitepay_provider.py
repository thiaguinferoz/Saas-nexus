from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import httpx

from app.config import get_settings

PlanCode = Literal["common", "custom"]
BillingInterval = Literal["monthly", "annual"]


@dataclass(frozen=True, slots=True)
class PlanOffer:
    plan: PlanCode
    interval: BillingInterval
    amount_cents: int
    description: str


@dataclass(frozen=True, slots=True)
class InfinitePayCheckout:
    url: str


@dataclass(frozen=True, slots=True)
class InfinitePayPayment:
    paid: bool
    amount_cents: int
    paid_amount_cents: int | None
    installments: int
    capture_method: str


PLAN_OFFERS: dict[tuple[PlanCode, BillingInterval], PlanOffer] = {
    ("common", "monthly"): PlanOffer("common", "monthly", 60_000, "Nexus Comum - acesso por 1 mês"),
    ("common", "annual"): PlanOffer("common", "annual", 540_000, "Nexus Comum - acesso por 1 ano"),
    ("custom", "monthly"): PlanOffer("custom", "monthly", 100_000, "Nexus Personalizado - acesso por 1 mês"),
    ("custom", "annual"): PlanOffer("custom", "annual", 900_000, "Nexus Personalizado - acesso por 1 ano"),
}


class InfinitePayError(RuntimeError):
    pass


def get_plan_offer(plan: PlanCode, interval: BillingInterval) -> PlanOffer:
    try:
        return PLAN_OFFERS[(plan, interval)]
    except KeyError as exc:
        raise InfinitePayError("Plano ou período de cobrança inválido") from exc


def _valid_checkout_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return value


class InfinitePayBillingProvider:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        if not settings.infinitepay_handle:
            raise InfinitePayError("InfinitePay não configurada")
        self.handle = settings.infinitepay_handle.removeprefix("$")
        self.api_url = settings.infinitepay_api_url.rstrip("/")
        self._client = client

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            if self._client is not None:
                response = await self._client.post(f"{self.api_url}{path}", json=payload)
            else:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    response = await client.post(f"{self.api_url}{path}", json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise InfinitePayError("A InfinitePay não respondeu corretamente") from exc
        if not isinstance(data, dict):
            raise InfinitePayError("Resposta inválida da InfinitePay")
        return data

    async def create_checkout(
        self,
        *,
        order_nsu: str,
        offer: PlanOffer,
        customer_name: str,
        customer_email: str,
        redirect_url: str,
        webhook_url: str,
    ) -> InfinitePayCheckout:
        data = await self._post(
            "/links",
            {
                "handle": self.handle,
                "redirect_url": redirect_url,
                "webhook_url": webhook_url,
                "order_nsu": order_nsu,
                "customer": {"name": customer_name, "email": customer_email},
                "items": [
                    {
                        "quantity": 1,
                        "price": offer.amount_cents,
                        "description": offer.description,
                    }
                ],
            },
        )
        checkout_url = _valid_checkout_url(data.get("url"))
        if not checkout_url:
            raise InfinitePayError("A InfinitePay não retornou um checkout seguro")
        return InfinitePayCheckout(url=checkout_url)

    async def verify_payment(
        self,
        *,
        order_nsu: str,
        transaction_nsu: str,
        slug: str,
    ) -> InfinitePayPayment:
        data = await self._post(
            "/payment_check",
            {
                "handle": self.handle,
                "order_nsu": order_nsu,
                "transaction_nsu": transaction_nsu,
                "slug": slug,
            },
        )
        try:
            amount = int(data.get("amount"))
            paid_amount = int(data["paid_amount"]) if data.get("paid_amount") is not None else None
            installments = int(data.get("installments") or 1)
        except (TypeError, ValueError) as exc:
            raise InfinitePayError("Confirmação de pagamento inválida") from exc
        capture_method = data.get("capture_method")
        if capture_method not in {"pix", "credit_card"} or installments < 1 or installments > 12:
            raise InfinitePayError("Forma de pagamento inválida")
        return InfinitePayPayment(
            paid=bool(data.get("success") and data.get("paid")),
            amount_cents=amount,
            paid_amount_cents=paid_amount,
            installments=installments,
            capture_method=capture_method,
        )
