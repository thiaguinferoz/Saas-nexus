# Runbook da automação Nexus

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

O n8n nunca escolhe tenant, preço, plano ou credencial YCloud. Ele recebe um `execution_id`, busca um snapshot sanitizado e solicita ações ao FastAPI.

## 2. Serviços no Easypanel

Crie serviços independentes usando a mesma imagem de `apps/api/Dockerfile`:

| Serviço | Comando |
|---|---|
| `nexus-api` | comando padrão do Dockerfile |
| `nexus-outbox` | `python -m app.workers.outbox_dispatcher` |
| `nexus-automation-worker` | `python -m app.workers.automation_worker` |
| `nexus-outbound-worker` | `python -m app.workers.outbound_worker` |
| `nexus-provisioning-worker` | `python -m app.workers.provisioning_worker` |

Todos usam as mesmas variáveis da API e a mesma rede privada de PostgreSQL e Redis. Somente `nexus-api` recebe domínio público. Workers não recebem domínio.

Use `REDIS_STREAM_PREFIX=nexus`. Se o n8n usar a mesma instância Redis no MVP, configure o queue mode dele no database lógico `1` e prefixo `n8n`; a Nexus permanece no database `0`. Em produção com maior volume, separe as instâncias.

## 3. Variáveis obrigatórias

Copie `.env.example` para os quatro serviços Python. Valores que precisam ser iguais:

- `N8N_SERVICE_TOKEN`: token aleatório com pelo menos 64 caracteres;
- `N8N_INTERNAL_WEBHOOK_URL`: endereço privado do webhook publicado pelo n8n;
- `N8N_WEBHOOK_HEADER_NAME=X-Nexus-Token`;
- `YCLOUD_API_KEY` e `YCLOUD_WEBHOOK_SECRET`;
- `DATABASE_URL` e `REDIS_URL` privados.

No serviço n8n, use `.env.n8n.example` como referência. `N8N_ENCRYPTION_KEY` precisa ser permanente; trocar essa chave perde o acesso às credenciais cifradas já salvas.

## 4. Preparar o workflow no n8n

1. Importe `NEXUS - WORKFLOW BASE MULTITENANT.json` e `NEXUS - ERROR HANDLER.json`.
2. Crie a credencial Header Auth `Nexus Internal Webhook`:
   - Header: `X-Nexus-Token`;
   - Value: o mesmo valor de `N8N_SERVICE_TOKEN`.
3. Crie a credencial Header Auth `Nexus FastAPI Service`:
   - Header: `X-Service-Token`;
   - Value: o mesmo valor de `N8N_SERVICE_TOKEN`.
4. Selecione `Nexus Internal Webhook` no nó `Entrada Nexus (FastAPI)`.
5. Selecione `Nexus FastAPI Service` em `Contexto Nexus`, `Marcar execução em andamento`, `Indicador de digitação via FastAPI`, `Baixar imagem YCloud`, `Baixar audio YCloud`, `Solicitar envio ao FastAPI`, `Confirmar execução no FastAPI` e `Reportar falha ao FastAPI` no workflow de erro.
6. Reconecte somente as credenciais Redis e Google Gemini já usadas pelo motor. A credencial da YCloud não fica mais dentro do n8n.
7. Confirme que `NEXUS_API_INTERNAL_URL` resolve a API pela rede privada.
8. No workflow principal, configure `NEXUS - ERROR HANDLER` como workflow de erro.
9. Ative os dois workflows e copie a URL de produção `/webhook/nexus-automation-v1` para `N8N_INTERNAL_WEBHOOK_URL` dos workers.

O arquivo é gerado por `tools/build_multitenant_workflow.ps1`. Mudanças reutilizáveis devem ser feitas no script e depois regeneradas; não mantenha edições divergentes apenas dentro do editor do n8n.

## 5. Configurar a YCloud

Cadastre um único endpoint global:

```text
https://api.seudominio.com.br/v1/webhooks/ycloud
```

Salve o segredo emitido pela YCloud em `YCLOUD_WEBHOOK_SECRET`. O FastAPI valida o corpo bruto e `YCloud-Signature` antes de aceitar o evento.

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
- `nexus:dlq`: tarefas que atingiram o limite de tentativas.

Os workers usam consumer groups, `XACK` somente após sucesso e `XAUTOCLAIM` para recuperar tarefas abandonadas. O limite padrão é cinco tentativas.

## 9. Checklist de ativação

1. API responde `/health`.
2. PostgreSQL e Redis não possuem porta pública.
3. Os quatro workers estão `running` sem reinícios contínuos.
4. Workflow Nexus está ativo e usa URL de produção.
5. Credenciais Header Auth foram selecionadas na entrada, nos sete nós do workflow principal que chamam o FastAPI e no workflow de erro.
6. Um tenant possui assinatura ativa, configuração e WhatsApp conectado.
7. Uma mensagem de teste cria uma linha em `workflow_executions`.
8. A execução chega ao n8n e cria uma linha em `outbound_messages`.
9. A mensagem chega uma única vez ao WhatsApp.
10. `nexus:dlq` permanece vazia.

## 10. Próxima fase

Depois do primeiro teste real, implementar:

- indicadores de `sent/delivered/read/failed` no painel (a atualização no banco já está preparada);
- endpoint administrativo de replay da DLQ com auditoria;
- métricas de latência e erro por tenant;
- ensaiar upgrade e rollback das migrações em staging antes de cada release;
- alerta operacional quando o workflow de erro enviar callback `failed`;
- limites de uso e rate limit por tenant/número.
