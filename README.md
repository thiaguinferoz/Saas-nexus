# SaaS de Automação de WhatsApp

Fundação do produto self-service com landing page, painel multi-tenant e API central.

## Estrutura

- `apps/web`: landing e painel em Next.js/TypeScript.
- `apps/api`: API FastAPI, autenticação e configurações multi-tenant.
- `compose.yml`: referência de infraestrutura para Easypanel/VPS.
- `ARQUITETURA_E_ROADMAP.md`: decisões, provisionamento e roadmap.
- `IA VET CAIÇARA - BASE SEM CATALOGO.json`: workflow n8n de referência.

## Primeira implantação no Easypanel

1. Envie este repositório para um Git remoto privado.
2. Crie PostgreSQL e Redis como serviços privados persistentes.
3. Crie o serviço da API apontando para `apps/api/Dockerfile`.
4. Crie o serviço web apontando para `apps/web/Dockerfile`.
5. Configure as variáveis de `.env.example` no painel, sem versionar valores reais.
6. Publique `api.seudominio.com.br` para a API e `app.seudominio.com.br` para o web.
7. Execute `alembic upgrade head` com `AUTO_CREATE_TABLES=false` e confirme `/health`; veja `AUTOMACAO_RUNBOOK.md`.

## Estado desta primeira entrega

- Cadastro cria usuário, tenant, membership owner e configuração inicial em uma transação.
- Login usa cookie seguro e HttpOnly.
- Preferências possuem versão e bloqueio de sobrescrita concorrente com `If-Match`.
- Landing, cadastro, login e painel configurável estão implementados.
- O painel salva empresa, timezone, horários, tom, instruções e fallback humano.
- O n8n pode consultar o contexto ativo por uma rota interna autenticada com token de serviço.
- Billing via Stripe, Checkout, Portal e webhooks idempotentes estão implementados.
- Embedded Signup/YCloud possui sessão segura, vínculo por tenant, webhook HMAC idempotente e tela de conexão no painel.
- Para validar a conexão real, ainda é necessário configurar as credenciais de parceiro Meta/YCloud descritas em `.env.example`.
- Dispatcher da outbox, Redis Streams, workers de automação/saída, snapshots de execução e callbacks FastAPI ↔ n8n estão implementados.
- O workflow genérico está em `NEXUS - WORKFLOW BASE MULTITENANT.json`; o passo a passo de implantação está em `AUTOMACAO_RUNBOOK.md`.
