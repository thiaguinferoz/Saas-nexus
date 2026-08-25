import asyncio

from app.ycloud.client import YCloudClient


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "id": "phone-number-123",
            "phoneNumber": "+5513999990000",
            "wabaId": "waba/with spaces",
            "status": "PENDING",
        }


class FakeAsyncClient:
    request: tuple[str, dict] | None = None

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, path: str, **kwargs: object) -> FakeResponse:
        FakeAsyncClient.request = (path, kwargs)
        return FakeResponse()


def test_bind_coexistence_waba_uses_smb_partner_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.ycloud.client.httpx.AsyncClient", FakeAsyncClient)
    client = object.__new__(YCloudClient)
    client.base_url = "https://api.ycloud.com/v2"
    client.headers = {"X-API-Key": "test-key"}

    result = asyncio.run(client.bind_coexistence_waba(waba_id="waba/with spaces"))

    assert result["id"] == "phone-number-123"
    assert FakeAsyncClient.request == (
        "/whatsapp/businessAccounts/waba%2Fwith%20spaces/smb/bind",
        {"headers": {"X-API-Key": "test-key"}},
    )
