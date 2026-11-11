param([string]$NomeTarefa = 'Ferezini - E-mails pendentes')
$ErrorActionPreference = 'Stop'
$caminhoScript = Join-Path $PSScriptRoot 'processar_emails.ps1'
$acao = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}"' -f $caminhoScript) -WorkingDirectory ((Resolve-Path (Join-Path $PSScriptRoot '../..')).Path)
$gatilho = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$configuracao = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho -Settings $configuracao -Description 'Processa a fila persistente do Ferezini a cada minuto.'
Write-Host 'Tarefa criada para o usuário atual. Configure conta de serviço e execução sem login nas propriedades do Agendador em produção.'
