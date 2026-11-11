$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$env:DJANGO_SETTINGS_MODULE = 'config.settings.production'
& ./.venv/Scripts/python.exe manage.py processar_emails_pendentes
if ($LASTEXITCODE -ne 0) { throw 'Falha no processamento de e-mails. Consulte os registros.' }
