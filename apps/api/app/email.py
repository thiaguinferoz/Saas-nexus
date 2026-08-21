import html
import uuid

import httpx

from app.config import get_settings


class EmailDeliveryError(RuntimeError):
    pass


class TransactionalEmailService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.resend_api_key:
            raise EmailDeliveryError("Serviço de e-mail ainda não configurado")

    async def send(self, *, to: str, subject: str, html_body: str, idempotency_key: str, reply_to: str | None = None) -> None:
        headers = {
            "Authorization": f"Bearer {self.settings.resend_api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key[:256],
            "User-Agent": "Nexus-SaaS/1.0",
        }
        payload: dict[str, object] = {
            "from": self.settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html_body,
        }
        if reply_to or self.settings.email_reply_to:
            payload["reply_to"] = reply_to or self.settings.email_reply_to
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post("https://api.resend.com/emails", headers=headers, json=payload)
        if response.status_code >= 400:
            raise EmailDeliveryError("Não foi possível enviar o e-mail agora")

    async def send_verification(self, *, to: str, name: str, token: str, token_id: uuid.UUID) -> None:
        url = f"{self.settings.frontend_url}/verificar-email?token={token}"
        safe_name = html.escape(name)
        await self.send(
            to=to,
            subject="Confirme seu e-mail na Nexus",
            idempotency_key=f"verify-{token_id}",
            html_body=_email_layout(
                title="Confirme seu e-mail",
                body=f"Olá, {safe_name}. Confirme seu endereço para ativar sua conta e iniciar seus 3 dias grátis.",
                button_label="Confirmar meu e-mail",
                button_url=url,
                footnote="Este link expira em 24 horas. Se você não criou esta conta, ignore esta mensagem.",
            ),
        )

    async def send_password_reset(self, *, to: str, name: str, token: str, token_id: uuid.UUID) -> None:
        url = f"{self.settings.frontend_url}/redefinir-senha?token={token}"
        safe_name = html.escape(name)
        await self.send(
            to=to,
            subject="Redefina sua senha da Nexus",
            idempotency_key=f"reset-{token_id}",
            html_body=_email_layout(
                title="Redefinição de senha",
                body=f"Olá, {safe_name}. Recebemos uma solicitação para criar uma nova senha para sua conta.",
                button_label="Criar nova senha",
                button_url=url,
                footnote="Este link expira em 60 minutos. Se não foi você, nenhuma alteração será feita.",
            ),
        )

    async def send_support_ticket(
        self,
        *,
        to: str,
        requester_email: str,
        requester_name: str,
        company_name: str,
        ticket_id: uuid.UUID,
        category: str,
        priority: str,
        subject: str,
        message: str,
        preferred_channel: str,
        contact_value: str | None,
    ) -> None:
        details = (
            f"<strong>Empresa:</strong> {html.escape(company_name)}<br>"
            f"<strong>Solicitante:</strong> {html.escape(requester_name)} ({html.escape(requester_email)})<br>"
            f"<strong>Categoria:</strong> {html.escape(category)}<br>"
            f"<strong>Prioridade:</strong> {html.escape(priority)}<br>"
            f"<strong>Retorno:</strong> {html.escape(preferred_channel)}"
        )
        if contact_value:
            details += f" — {html.escape(contact_value)}"
        details += f"<br><br><strong>Mensagem:</strong><br>{html.escape(message).replace(chr(10), '<br>')}"
        await self.send(
            to=to,
            subject=f"[Nexus] {subject}",
            idempotency_key=f"support-{ticket_id}",
            reply_to=requester_email,
            html_body=_email_layout(
                title="Nova solicitação de suporte",
                body=details,
                button_label="Abrir painel Nexus",
                button_url=f"{self.settings.frontend_url}/app",
                footnote=f"Ticket {ticket_id}. A solicitação também permanece registrada no banco da plataforma.",
            ),
        )


def _email_layout(*, title: str, body: str, button_label: str, button_url: str, footnote: str) -> str:
    safe_url = html.escape(button_url, quote=True)
    return f"""
    <!doctype html><html lang="pt-BR"><body style="margin:0;background:#f3f4fb;font-family:Arial,sans-serif;color:#18213f">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:36px 16px">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#fff;border-radius:20px;overflow:hidden;border:1px solid #e1e3f1">
          <tr><td style="padding:28px 32px;background:linear-gradient(135deg,#151d54,#6842d9);color:#fff"><strong style="font-size:21px;letter-spacing:1px">NEXUS</strong><div style="font-size:11px;color:#c8c8ef;margin-top:5px">automações inteligentes</div></td></tr>
          <tr><td style="padding:34px 32px"><h1 style="margin:0 0 16px;font-size:25px">{html.escape(title)}</h1><p style="margin:0 0 25px;line-height:1.65;color:#59627d">{body}</p><a href="{safe_url}" style="display:inline-block;padding:14px 20px;border-radius:11px;background:#6542d9;color:#fff;text-decoration:none;font-weight:700">{html.escape(button_label)}</a><p style="margin:27px 0 0;font-size:12px;line-height:1.55;color:#8a91a8">{html.escape(footnote)}</p></td></tr>
        </table>
      </td></tr></table>
    </body></html>
    """
