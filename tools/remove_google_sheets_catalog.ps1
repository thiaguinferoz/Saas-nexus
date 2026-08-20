param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

$root = Get-Content -LiteralPath $InputPath -Raw | ConvertFrom-Json
$workflows = @($root)
$removedNodeNames = @('Ler catálogo atualizado', 'Selecionar itens do catálogo')

foreach ($workflow in $workflows) {
    $workflow.nodes = @($workflow.nodes | Where-Object { $_.name -notin $removedNodeNames })

    foreach ($nodeName in $removedNodeNames) {
        $workflow.connections.PSObject.Properties.Remove($nodeName)
    }

    $questionConnections = $workflow.connections.'Pergunta sobre funcionamento agora?'.main
    if ($questionConnections.Count -lt 2) {
        throw 'A saída esperada do nó "Pergunta sobre funcionamento agora?" não foi encontrada.'
    }

    $questionConnections[1] = @(
        [pscustomobject]@{
            node = 'AI Agent'
            type = 'main'
            index = 0
        }
    )

    $agent = $workflow.nodes | Where-Object { $_.name -eq 'AI Agent' } | Select-Object -First 1
    if ($null -eq $agent) {
        throw 'O nó "AI Agent" não foi encontrado.'
    }

    $agent.parameters.text = @'
={{
  'CONTEXTO OPERACIONAL OBRIGATÓRIO\n' +
  'DATA: ' + ($json.dataSaoPaulo || 'não informada') + '\n' +
  'DIA: ' + ($json.diaSemanaSaoPaulo || 'não informado') + '\n' +
  'HORÁRIO: ' + ($json.horarioSaoPaulo || 'não informado') + '\n' +
  'FUNCIONAMENTO DE HOJE: ' + ($json.horarioFuncionamentoHoje || 'não informado') + '\n' +
  'STATUS DEFINITIVO: ' + ($json.clinicaAbertaAgora === true ? 'ABERTA' : 'FECHADA') + '\n' +
  'PRÓXIMA ABERTURA: ' + ($json.proximaAbertura || 'não se aplica') + '\n' +
  'Nunca contradiga esses dados e nunca use o status de mensagens anteriores. Use o status somente quando o cliente perguntar sobre funcionamento, pedir atendimento presencial ou quando ele for necessário para um encaminhamento seguro. Em uma saudação simples, não mencione horário nem status.\n\n' +
  'REGRAS PARA ENTRADAS AGRUPADAS\n' +
  '- A entrada pode conter texto, transcrição de áudio e análise de imagem enviados em sequência pelo mesmo cliente.\n' +
  '- Interprete todos os blocos como uma única solicitação, respeitando a ordem apresentada e relacionando pronomes como “isso”, “ele” e “serve para isso” à mídia e ao texto próximos.\n' +
  '- Se houver [ANÁLISE VISUAL DA IMAGEM] ou [ANÁLISE VISUAL INDISPONÍVEL], a imagem já foi recebida. Nunca peça ao cliente para enviar a foto novamente, exceto se a própria análise disser que ela está insuficiente, escura, cortada ou desfocada.\n' +
  '- Se houver [TRANSCRIÇÃO DO ÁUDIO], o áudio já foi recebido e transcrito.\n' +
  '- Responda a todos os assuntos em UMA ÚNICA mensagem de WhatsApp, sem criar respostas separadas e sem ignorar nenhum pedido.\n' +
  '- SAUDAÇÃO OBRIGATÓRIA: se a entrada atual contiver “olá”, “oi”, “bom dia”, “boa tarde” ou “boa noite” como cumprimento, comece a resposta com um cumprimento equivalente antes de responder ao assunto.\n' +
  '- Cumprimente apenas uma vez. Não acrescente saudação quando o cliente não tiver cumprimentado e não repita uma saudação que já esteja no início da resposta.\n' +
  '- Quando o cliente apenas confirmar uma visita ou horário que já informou, confirme de forma breve sem repetir o horário, salvo se for necessário corrigir uma divergência.\n\n' +
  'MENSAGEM DO CLIENTE:\n' + String($json.message || '')
}}
'@

    $systemMessage = [string]$agent.parameters.options.systemMessage
    $paragraphs = [regex]::Split($systemMessage, '(?:\r?\n){2,}')
    $keptParagraphs = @($paragraphs | Where-Object {
        $_ -notmatch '(?i)cat[aá]logo|planilha|catalogoResultados|catalogoConsultado|Produto / Servi[cç]o'
    })
    $agent.parameters.options.systemMessage = ($keptParagraphs -join "`n`n")
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

$json = if ($root -is [System.Array]) {
    ConvertTo-Json -InputObject @($workflows) -Depth 100
} else {
    ConvertTo-Json -InputObject $workflows[0] -Depth 100
}

[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
