# Runbook da automação Nexus

Este documento descreve componentes implementados no repositório e o procedimento para ativá-los. A existência do código não comprova que Stripe, Resend, Meta/YCloud ou n8n estejam configurados ou funcionais no ambiente. O aceite de produção exige os testes de `DEPLOY_CHECKLIST.md`.

## 1. Resultado desta fase

O fluxo padrão deixou de ser um webhook YCloud isolado por cliente. Agora existe uma única esteira multi-tenant:

```text
YCloud
  → POST /v1/webhooks/ycloud
  → PostgreSQL (webhook + execução + outbox, na mesma transação)
  → outbox-dispatcher
  → Redis Stream nexus:automation
  → automation-worker
  → Webhook interno do workflow n8n
  → GET /internal/v1/executions/{id}/context
  → POST /internal/v1/messages
  → Redis Stream nexus:outbound
  → outbound-worker
  → fila assíncrona de mensagens da YCloud
```

Quando a integração estiver configurada e validada, o n8n nunca escolherá tenant, preço, plano ou credencial YCloud. Ele receberá um `execution_id`, buscará um snapshot sanitizado e solicitará ações ao FastAPI.

As notificações de suporte seguem uma fila separada:

```text
POST /v1/support/tickets
  → PostgreSQL (ticket + outbox)
  → outbox-dispatcher
  → Redis Stream nexus:support
  → support-worker
  → Resend
```

## 2. Serviços no Easypanel

Crie serviços independentes usando a mesma imagem de `apps/api/Dockerfile`:

| Serviço | Comando |
|---|---|
| `nexus-api` | comando padrão do Dockerfile |
| `nexus-outbox` | `python -m app.workers.outbox_dispatcher` |
| `nexus-automation-worker` | `python -m app.workers.automation_worker` |
| `nexus-outbound-worker` | `python -m app.workers.outbound_worker` |
| `nexus-provisioning-worker` | `python -m app.workers.provisioning_worker` |
| `support-worker` | `python -m app.workers.support_worker` |

Todos usam as mesmas variáveis da API e a mesma rede privada de PostgreSQL e Redis. Somente `nexus-api` recebe domínio público. Workers não recebem domínio. O serviço n8n deve usar banco e credenciais PostgreSQL próprios, mesmo quando compartilhar a infraestrutura física no MVP.

Use `REDIS_STREAM_PREFIX=nexus`. Se o n8n usar a mesma instância Redis no MVP, configure o queue mode dele no database lógico `1` e prefixo `n8n`; a Nexus permanece no database `0`. Em produção com maior volume, separe as instâncias.

## 3. Variáveis obrigatórias

Use `.env.example` como referência para todos os serviços Python. Não copie valores de exemplo para produção. Valores que precisam ser iguais:

- `N8N_SERVICE_TOKEN`: token aleatório com pelo menos 64 caracteres;
- `N8N_INTERNAL_WEBHOOK_URL`: endereço privado do webhook publicado pelo n8n;
- `N8N_WEBHOOK_HEADER_NAME=X-Nexus-Token`;
- `DATABASE_URL` e `REDIS_URL` privados.

Dependências por integração:

- Resend: `RESEND_API_KEY`, `EMAIL_FROM` com remetente verificado e, para notificações internas, `SUPPORT_EMAIL`;
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` e `STRIPE_PRICE_ID` pertencentes ao mesmo modo, além de `TRIAL_DAYS` e `BILLING_GRACE_DAYS` revisados;
- Meta/YCloud: `YCLOUD_API_KEY`, `YCLOUD_WEBHOOK_SECRET`, `META_APP_ID` e `META_EMBEDDED_SIGNUP_CONFIG_ID` com permissões válidas;
- n8n: `N8N_HOST`, `N8N_ENCRYPTION_KEY` permanente e `N8N_POSTGRES_DB`, `N8N_POSTGRES_USER`, `N8N_POSTGRES_PASSWORD` exclusivos no Compose. `.env.n8n.example` documenta os nomes que chegam ao processo n8n.

No serviço n8n, use `.env.n8n.example` como referência. `N8N_ENCRYPTION_KEY` precisa ser permanente; trocar ou perder essa chave remove o acesso às credenciais já cifradas. Nunca implante o n8n apontando para o banco e o usuário da aplicação Nexus.

## 4. Preparar o workflow no n8n

1. Importe `NEXUS - WORKFLOW BASE MULTITENANT.json` e `NEXUS - ERROR HANDLER.json`; subir o container não faz essa importação automaticamente.
2. Crie a credencial Header Auth `Nexus Internal Webhook`:
   - Header: `X-Nexus-Token`;
   - Value: o mesmo valor de `N8N_SERVICE_TOKEN`.
3. Crie a credencial Header Auth `Nexus FastAPI Service`:
   - Header: `X-Service-Token`;
   - Value: o mesmo valor de `N8N_SERVICE_TOKEN`.
4. Selecione `Nexus Internal Webhook` no nó `Entrada Nexus (FastAPI)`.
5. Selecione `Nexus FastAPI Service` em `Contexto Nexus`, `Marcar execução em andamento`, `Indicador de digitação via FastAPI`, `Baixar imagem YCloud`, `Baixar audio YCloud`, `Solicitar envio ao FastAPI`, `Confirmar execução no FastAPI` e `Reportar falha ao FastAPI` no workflow de erro.
6. Reconecte somente as credenciais Redis e Google Gemini já usadas pelo motor. A credencial da YCloud não fica mais dentro do n8n.
7. Confirme que o hostname interno `api` resolve na rede privada; os workflows versionados usam a base não secreta fixa `http://api:8000` e não leem variáveis de ambiente em expressões.
8. Confirme que o workflow principal está vinculado ao `NEXUS - ERROR HANDLER`; o JSON versionado já usa o ID determinístico `NEXUSERRHANDLER1`.
9. Publique os dois workflows e copie a URL de produção `/webhook/nexus-automation-v1` para `N8N_INTERNAL_WEBHOOK_URL` dos workers.
10. Faça uma chamada controlada e confirme uma execução no n8n antes de liberar tráfego real.

Os dois arquivos JSON são gerados por `tools/build_multitenant_workflow.ps1`. A constante `$NexusApiBase` mantém a base interna em um único ponto do gerador. Mudanças reutilizáveis devem ser feitas no script e depois regeneradas; não mantenha edições divergentes apenas dentro do editor do n8n. O acesso de expressões às variáveis do processo n8n deve permanecer bloqueado.

## 5. Configurar a YCloud

Depois que as credenciais e permissões de parceiro estiverem confirmadas, cadastre um único endpoint global:

```text
https://api.seudominio.com.br/v1/webhooks/ycloud
```

Salve o segredo emitido pela YCloud em `YCLOUD_WEBHOOK_SECRET`. O FastAPI valida o corpo bruto e `YCloud-Signature` antes de aceitar o evento. A presença dessa validação no código não substitui um teste assinado real ou de sandbox.

Assine pelo menos os eventos:

- `whatsapp.inbound_message.received`;
- `whatsapp.message.updated`;
- `whatsapp.phone_number.deleted`.

## 6. Banco de dados

Esta fase adiciona `workflow_executions` e `outbound_messages`, com migração em `apps/api/migrations`.

Para uma instalação nova e vazia:

1. configure `AUTO_CREATE_TABLES=false` desde o início;
2. execute `alembic upgrade head` usando a imagem da API;
3. suba a API e os workers.

Para uma instalação que já possui as tabelas anteriores, mas ainda não possui as duas tabelas desta fase:

1. faça backup do PostgreSQL;
2. execute `alembic stamp 20260820_00` para registrar a estrutura anterior como baseline;
3. execute `alembic upgrade head` para criar somente as tabelas da automação;
4. suba API e workers com `AUTO_CREATE_TABLES=false`.

Se o `create_all` já tiver criado também `workflow_executions` e `outbound_messages`, use apenas `alembic stamp head`. Ensaie backup/restore antes do beta e nunca altere tabelas manualmente em produção.

## 7. Contratos do workflow

Entrada do webhook n8n:

```json
{
  "schema_version": "1.0",
  "execution_id": "uuid",
  "tenant_id": "uuid",
  "correlation_id": "uuid"
}
```

O contexto retorna a configuração exata que estava ativa quando o evento chegou. Alterações posteriores do prompt não mudam uma execução em andamento.

O envio usa `idempotency_key={execution_id}:reply:v1`. Repetir o nó, reiniciar worker ou receber o webhook outra vez não cria uma segunda mensagem no banco.

## 8. Filas e falhas

- `nexus:automation`: tarefas que disparam o workflow padrão;
- `nexus:outbound`: mensagens aprovadas para envio;
- `nexus:provisioning`: eventos de provisionamento e cobrança;
- `nexus:support`: notificações de chamados para a equipe de suporte;
- `nexus:dlq`: tarefas que atingiram o limite de tentativas.

Os workers usam consumer groups, `XACK` somente após sucesso e `XAUTOCLAIM` para recuperar tarefas abandonadas. O limite padrão é cinco tentativas.

## 9. Checklist de ativação

1. API responde `/health`.
2. PostgreSQL e Redis não possuem porta pública.
3. Todos os workers declarados no deploy estão `running` sem reinícios contínuos.
4. Workflow Nexus está ativo e usa URL de produção.
5. Credenciais Header Auth foram selecionadas na entrada, nos sete nós do workflow principal que chamam o FastAPI e no workflow de erro.
6. Um tenant possui assinatura ativa, configuração e WhatsApp conectado.
7. Uma mensagem de teste cria uma linha em `workflow_executions`.
8. A execução chega ao n8n e cria uma linha em `outbound_messages`.
9. A mensagem chega uma única vez ao WhatsApp.
10. `nexus:dlq` permanece vazia.
11. Stripe, Resend e Meta/YCloud foram validados separadamente conforme `DEPLOY_CHECKLIST.md`; nenhuma credencial ainda contém placeholder.
12. Uma solicitação de suporte é persistida, consumida pelo `support-worker` e marcada como notificada após entrega pelo Resend.

## 10. Próxima fase

Depois do primeiro teste real, implementar:

- indicadores de `sent/delivered/read/failed` no painel (a atualização no banco já está preparada);
- endpoint administrativo de replay da DLQ com auditoria;
- métricas de latência e erro por tenant;
- ensaiar upgrade e rollback das migrações em staging antes de cada release;
- alerta operacional quando o workflow de erro enviar callback `failed`;
- limites de uso e rate limit por tenant/número.
