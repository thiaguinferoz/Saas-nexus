# Checklist de deploy da Nexus

Use este roteiro para staging e produção. Marque um item somente após observar a evidência correspondente. Nunca registre chaves, tokens ou senhas neste arquivo, em commits, capturas de tela ou logs.

## 1. Identificar a versão e preparar retorno

- [ ] Registrar branch, commit e responsável pela janela de deploy.
- [ ] Confirmar que o commit remoto é exatamente o que o Easypanel buscará.
- [ ] Registrar o último commit funcional, as imagens atuais e a revisão Alembic atual.
- [ ] Definir critérios objetivos para abortar: falha de migração, API sem saúde, login indisponível, workers reiniciando ou aumento relevante de erros.
- [ ] Confirmar que existe espaço em disco para imagens, volumes e backup.

## 2. Backup antes de qualquer migração

- [ ] Gerar backup consistente do PostgreSQL da aplicação e guardar fora do volume do container.
- [ ] Validar que o backup pode ser lido e registrar o procedimento de restauração.
- [ ] Fazer backup separado do banco e do volume do n8n.
- [ ] Preservar `N8N_ENCRYPTION_KEY`; o banco e o volume do n8n não bastam sem essa chave.
- [ ] Registrar a revisão com `alembic current` antes da alteração.

Não use `alembic stamp` apenas para contornar um erro. Primeiro compare o schema real com a migração esperada. Para bancos antigos criados por `create_all`, siga a seção de banco em `AUTOMACAO_RUNBOOK.md`.

## 3. Conferir variáveis sem expor valores

### Aplicação e infraestrutura

- [ ] `APP_ENV=production`.
- [ ] `APP_SECRET_KEY`, `DATABASE_URL` e `REDIS_URL` estão presentes e não usam valores de exemplo.
- [ ] `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` e `REDIS_PASSWORD` correspondem às URLs internas.
- [ ] `FRONTEND_URL`, `COOKIE_DOMAIN` e `COOKIE_SECURE=true` correspondem ao domínio público.
- [ ] `AUTO_CREATE_TABLES=false`.
- [ ] `NEXT_PUBLIC_API_URL` termina em `/v1` e foi fornecida como argumento do build web.
- [ ] `NEXT_PUBLIC_MARKETING_URL` aponta para a landing page e foi fornecida como argumento do build web.
- [ ] Se o Compose usa `env_file: .env`, a opção do Easypanel que cria o arquivo `.env` está habilitada.

### Resend e suporte

- [ ] `RESEND_API_KEY` pertence ao ambiente correto e possui permissão de envio.
- [ ] `EMAIL_FROM` usa um endereço do domínio verificado no Resend.
- [ ] `EMAIL_REPLY_TO` está definido quando respostas precisam chegar a uma caixa monitorada.
- [ ] `SUPPORT_EMAIL` aponta para uma caixa monitorada.
- [ ] Tempos de expiração de confirmação e redefinição foram revisados.

### Stripe

- [ ] `BILLING_PROVIDER=stripe`.
- [ ] `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` e `STRIPE_PRICE_ID` são reais e pertencem todos ao mesmo modo: teste ou produção.
- [ ] O Price é recorrente, usa a moeda e o intervalo esperados e está ativo.
- [ ] `TRIAL_DAYS` corresponde à oferta publicada.
- [ ] `BILLING_GRACE_DAYS` corresponde à política de inadimplência publicada.

### n8n e automação

- [ ] `N8N_SERVICE_TOKEN` é forte e é o mesmo na API, nos workers e nas credenciais Header Auth do workflow.
- [ ] `N8N_INTERNAL_WEBHOOK_URL` resolve pela rede privada e termina em `/webhook/nexus-automation-v1`.
- [ ] `N8N_WEBHOOK_HEADER_NAME` corresponde ao header configurado no workflow.
- [ ] `N8N_HOST` e `N8N_ENCRYPTION_KEY` permanente estão definidos.
- [ ] O hostname `api` resolve pela rede privada em `http://api:8000`, base não secreta fixada nos workflows versionados.
- [ ] `N8N_POSTGRES_DB`, `N8N_POSTGRES_USER` e `N8N_POSTGRES_PASSWORD` são exclusivos; o n8n não usa o banco da aplicação Nexus.
- [ ] Se o n8n usa queue mode, Redis DB/prefixo são separados das streams `nexus:*`.

### Meta/YCloud

- [ ] `YCLOUD_API_KEY`, `YCLOUD_WEBHOOK_SECRET`, `META_APP_ID` e `META_EMBEDDED_SIGNUP_CONFIG_ID` são reais.
- [ ] A conta possui as permissões de parceiro exigidas e o ambiente escolhido está liberado.

Antes de continuar, procurar explicitamente por valores como `troque`, `seudominio`, `...` ou IDs ilustrativos. O deploy pode subir com placeholders e ainda assim deixar a funcionalidade quebrada.

## 4. Domínios, TLS e exposição

- [ ] `app.seudominio` aponta para `web:3000` e abre com TLS válido.
- [ ] `api.seudominio` aponta para `api:8000`; `/health` responde sem redirecionamento incorreto.
- [ ] `n8n.seudominio` aponta para `n8n:5678` quando o editor ou webhooks externos precisam ser acessíveis.
- [ ] `FRONTEND_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_MARKETING_URL`, `N8N_HOST`, `N8N_WEBHOOK_URL` e os domínios do Easypanel são coerentes entre si.
- [ ] PostgreSQL, Redis, serviços de migração e workers não possuem domínio nem porta pública.
- [ ] O editor n8n está protegido por SSO, VPN ou restrição de IP; publicar apenas o necessário não expõe credenciais administrativas.

## 5. Preparar Stripe e webhooks externos

- [ ] Cadastrar no Stripe o endpoint `https://api.seudominio/v1/webhooks/stripe`.
- [ ] Assinar os eventos realmente tratados pela versão implantada e copiar o novo signing secret para `STRIPE_WEBHOOK_SECRET`.
- [ ] Cadastrar na YCloud o endpoint `https://api.seudominio/v1/webhooks/ycloud` e os eventos listados em `AUTOMACAO_RUNBOOK.md`.
- [ ] Confirmar que firewalls, proxy e limites de corpo permitem os webhooks, sem desabilitar a validação de assinatura.

## 6. Preparar Resend

- [ ] Verificar o domínio remetente e os registros DNS exigidos pelo Resend.
- [ ] Confirmar que o endereço exato de `EMAIL_FROM` é aceito.
- [ ] Enviar testes para provedores diferentes e verificar entrega, spam, links e remetente.
- [ ] Testar separadamente confirmação de conta, recuperação de senha e notificação de suporte.

## 7. Preparar o n8n

- [ ] Importar `NEXUS - WORKFLOW BASE MULTITENANT.json`.
- [ ] Importar `NEXUS - ERROR HANDLER.json`.
- [ ] Criar e selecionar as duas credenciais Header Auth descritas em `AUTOMACAO_RUNBOOK.md`.
- [ ] Reconectar apenas as credenciais Redis e Google Gemini necessárias ao motor.
- [ ] Definir `NEXUS - ERROR HANDLER` como workflow de erro do fluxo principal.
- [ ] Ativar os dois workflows e confirmar que a URL exibida é a URL de produção, não a de teste.
- [ ] Fazer uma execução controlada e confirmar callbacks para a API antes de liberar mensagens reais.

Subir o container n8n não importa nem ativa os arquivos JSON automaticamente.

## 8. Migrar e implantar

- [ ] Colocar o ambiente em janela de manutenção se a migração ou o rollback exigir indisponibilidade.
- [ ] Executar `alembic upgrade head` uma única vez com a imagem da nova API.
- [ ] Confirmar `alembic current` no head esperado antes de iniciar a API e os workers.
- [ ] Confirmar que o serviço de migração terminou com código zero.
- [ ] Fazer o deploy do commit registrado; salvar variáveis ou reiniciar containers não substitui o rebuild do Next.js.
- [ ] Confirmar que API, web, n8n e todos os workers permanecem estáveis, sem loop de reinício.

## 9. Smoke tests após o deploy

- [ ] `GET https://api.seudominio/health` retorna `200` e `status=ok`.
- [ ] Landing page, cadastro, login e painel carregam por HTTPS sem conteúdo misto.
- [ ] O logo em login/cadastro retorna à landing page correta.
- [ ] Uma conta nova recebe confirmação, confirma o e-mail, entra e recebe o período grátis esperado.
- [ ] A recuperação de senha entrega o e-mail e permite usar a nova senha uma única vez.
- [ ] Checkout e Portal Stripe abrem; um evento de teste atualiza a assinatura e a repetição do evento não duplica efeitos.
- [ ] Uma solicitação de suporte fica registrada e sua notificação chega ao destino configurado.
- [ ] O `support-worker` consome `nexus:support`, registra a entrega e não entra em loop de reenvio.
- [ ] Um evento YCloud assinado cria uma execução, percorre Redis e n8n e gera no máximo uma mensagem de saída.
- [ ] `nexus:dlq` continua vazia após os testes.
- [ ] Logs não contêm tokens, senhas, dados de pagamento ou chaves completas.
- [ ] Não há aumento inesperado de respostas `5xx`, latência, CPU, memória ou reinícios.

## 10. Rollback

- [ ] Manter disponível o commit e as imagens da última versão funcional.
- [ ] Para falha somente de aplicação, reimplantar a versão anterior sem executar downgrade automático do banco.
- [ ] Confirmar que a versão anterior é compatível com o schema já migrado. Se não for, manter a manutenção e restaurar o backup seguindo procedimento aprovado.
- [ ] Nunca trocar `APP_SECRET_KEY`, `N8N_ENCRYPTION_KEY` ou volumes durante o rollback.
- [ ] Reverter separadamente domínios, webhooks e variáveis que tenham mudado.
- [ ] Após o retorno, repetir `/health`, login e o fluxo mínimo afetado.
- [ ] Registrar causa, horário, impacto, decisão e evidência da recuperação.

O rollback termina somente quando a versão anterior está estável e os dados foram verificados, não quando o comando de deploy termina.
