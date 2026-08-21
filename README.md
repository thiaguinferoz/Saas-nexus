# SaaS de Automação de WhatsApp

Fundação do produto self-service com landing page, painel multi-tenant e API central.

## Estrutura

- `apps/web`: landing e painel em Next.js/TypeScript.
- `apps/api`: API FastAPI, autenticação e configurações multi-tenant.
- `compose.yml`: referência de infraestrutura para Easypanel/VPS.
- `DEPLOY_CHECKLIST.md`: sequência operacional para preparar, implantar, validar e reverter uma versão.
- `ARQUITETURA_E_ROADMAP.md`: decisões, provisionamento e roadmap.
- `NEXUS - WORKFLOW BASE MULTITENANT.json`: workflow n8n versionado da Nexus.

## Primeira implantação no Easypanel

1. Envie este repositório para um Git remoto privado e registre o commit que será implantado.
2. Prepare PostgreSQL, Redis e os volumes persistentes sem expor portas públicas.
3. Configure as variáveis reais no Easypanel, sem versionar segredos e sem deixar valores de exemplo.
4. Confirme os domínios e certificados de `app`, `api` e `n8n`.
5. Faça backup do PostgreSQL, execute `alembic upgrade head` com `AUTO_CREATE_TABLES=false` e confirme `/health`.
6. Importe e ative os workflows do n8n e configure os webhooks externos antes do aceite.
7. Siga integralmente `DEPLOY_CHECKLIST.md`; salvar variáveis não substitui um novo deploy.

## Estado desta primeira entrega

- Cadastro, confirmação de e-mail, recuperação de senha e login estão implementados no código. O envio real depende de uma chave Resend válida e de um remetente verificado.
- Login usa cookie seguro e HttpOnly.
- Preferências possuem versão e bloqueio de sobrescrita concorrente com `If-Match`.
- Landing, cadastro, login e painel configurável estão implementados.
- O painel salva empresa, timezone, horários, tom, instruções e fallback humano.
- O contrato FastAPI ↔ n8n, as filas e os workers estão implementados no código, mas o fluxo só fica operacional após importar, credenciar, testar e ativar os dois workflows.
- O adapter de billing inclui Checkout, Portal e tratamento idempotente de webhooks Stripe. Pagamentos permanecem indisponíveis até configurar chaves reais, preço recorrente e endpoint de webhook no mesmo modo, teste ou produção.
- O Embedded Signup/YCloud possui os contratos de sessão, vínculo e webhook. A conexão real depende das credenciais, permissões de parceiro e validação ponta a ponta com Meta/YCloud.
- Notificações transacionais e de suporte dependem da configuração e da entrega confirmada no Resend.
- O passo a passo do motor está em `AUTOMACAO_RUNBOOK.md`; o aceite completo de produção está em `DEPLOY_CHECKLIST.md`.
