param([string]$Nssm = 'nssm.exe', [string]$NomeServico = 'Ferezini')
$ErrorActionPreference = 'Stop'
$raizProjeto = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonProjeto = Join-Path $raizProjeto '.venv/Scripts/python.exe'
if (-not (Get-Command $Nssm -ErrorAction SilentlyContinue)) { throw 'Instale NSSM e forneça -Nssm com seu caminho. Execute como administrador.' }
& $Nssm install $NomeServico $pythonProjeto '-m waitress --listen=127.0.0.1:8000 --threads=4 config.wsgi:application'
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível instalar o serviço.' }
& $Nssm set $NomeServico AppDirectory $raizProjeto
& $Nssm set $NomeServico AppEnvironmentExtra 'DJANGO_SETTINGS_MODULE=config.settings.production'
Write-Host 'Configure conta de serviço com acesso restrito ao .env e proxy HTTPS antes de iniciar o serviço.'
