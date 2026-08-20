from urllib.parse import quote

import httpx

from app.config import get_settings


class YCloudClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.ycloud_api_key:
            raise RuntimeError("YCloud não configurada")
        self.base_url = "https://api.ycloud.com/v2"
        self.headers = {"X-API-Key": self.settings.ycloud_api_key}

    async def retrieve_phone_number(self, *, waba_id: str, phone_number: str) -> dict:
        path = f"/whatsapp/phoneNumbers/{quote(waba_id, safe='')}/{quote(phone_number, safe='')}"
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15) as client:
            response = await client.get(path, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def send_text(self, *, sender: str, to: str, text: str, external_id: str, recipient_id: str | None = None, reply_to_message_id: str | None = None) -> dict:
        payload: dict = {"from": sender, "to": to, "type": "text", "text": {"body": text, "preview_url": False}, "externalId": external_id}
        if recipient_id:
            payload["recipient"] = recipient_id
        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.base_url}/whatsapp/messages", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def start_typing(self, *, inbound_message_id: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.base_url}/whatsapp/inboundMessages/{inbound_message_id}/typingIndicator", headers=self.headers)
            response.raise_for_status()

    async def download_media(self, *, url: str) -> tuple[bytes, str]:
        if not url.startswith("https://"):
            raise ValueError("URL de mídia inválida")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            content = response.content
            if len(content) > self.settings.media_proxy_max_bytes:
                raise ValueError("Mídia excede o limite da plataforma")
            return content, response.headers.get("content-type", "application/octet-stream")
