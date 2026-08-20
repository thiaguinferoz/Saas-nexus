import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class BillingSession:
    url: str
    customer_id: str | None = None


class BillingProvider(Protocol):
    async def create_checkout(
        self,
        *,
        tenant_id: uuid.UUID,
        customer_email: str,
        customer_id: str | None,
        success_url: str,
        cancel_url: str,
    ) -> BillingSession: ...

    async def create_portal(self, *, customer_id: str, return_url: str) -> BillingSession: ...

