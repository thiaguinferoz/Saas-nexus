param(
  [string]$Workflow = (Join-Path $PSScriptRoot '..\NEXUS - WORKFLOW BASE MULTITENANT.json'),
  [string]$ErrorWorkflow = (Join-Path $PSScriptRoot '..\NEXUS - ERROR HANDLER.json')
)

$raw = Get-Content -Raw -LiteralPath $Workflow
$data = $raw | ConvertFrom-Json -Depth 100
$required = @('Entrada Nexus (FastAPI)', 'Contexto Nexus', 'Marcar execução em andamento', 'Restaurar contexto Nexus', 'Dados', 'AI Agent', 'Baixar imagem YCloud', 'Baixar audio YCloud', 'Solicitar envio ao FastAPI', 'Confirmar execução no FastAPI')
$names = @($data.nodes.name)
$errors = [System.Collections.Generic.List[string]]::new()

foreach ($name in $required) {
  if ($name -notin $names) { $errors.Add("Nó obrigatório ausente: $name") }
}

foreach ($property in $data.connections.PSObject.Properties) {
  if ($property.Name -notin $names) { $errors.Add("Conexão parte de nó inexistente: $($property.Name)") }
  foreach ($output in $property.Value.main) {
    if ($output -isnot [array]) { $errors.Add("Saída do nó $($property.Name) não está no formato main[][] do n8n") }
    foreach ($target in $output) {
      if ($target.node -and $target.node -notin $names) { $errors.Add("Conexão aponta para nó inexistente: $($target.node)") }
    }
  }
}

foreach ($legacy in @('Vet Caiçara', 'Liga Vet', '3887-9961', 'vet-caicara-ycloud')) {
  if ($raw.Contains($legacy)) { $errors.Add("Conteúdo legado encontrado: $legacy") }
}

if ($raw.Contains('https://api.ycloud.com/v2/whatsapp/messages/sendDirectly')) {
  $errors.Add('O workflow não pode enviar mensagens diretamente pela YCloud')
}
if ($raw.Contains('Header Auth account')) {
  $errors.Add('Credencial YCloud legada ainda referenciada no workflow')
}

if ($errors.Count) {
  $errors | ForEach-Object { Write-Error $_ }
  exit 1
}

$errorRaw = Get-Content -Raw -LiteralPath $ErrorWorkflow
$errorData = $errorRaw | ConvertFrom-Json -Depth 30
if ('Erro do workflow' -notin @($errorData.nodes.name) -or 'Reportar falha ao FastAPI' -notin @($errorData.nodes.name)) {
  Write-Error 'Workflow de erro não contém os nós obrigatórios'
  exit 1
}

foreach ($candidate in @($raw, $errorRaw)) {
  if ($candidate.Contains('$env.') -or $candidate.Contains('NEXUS_API_INTERNAL_URL')) {
    Write-Error 'Workflow ainda depende de acesso amplo a variáveis de ambiente do n8n'
    exit 1
  }
  if (-not $candidate.Contains('http://api:8000/internal/v1/')) {
    Write-Error 'Workflow não contém a base interna esperada da API Nexus'
    exit 1
  }
}

Write-Output "Workflows válidos: $($data.nodes.Count) nós no fluxo principal, error handler presente e nenhuma regra legada."
