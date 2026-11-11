param([switch]$Producao)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($Producao) {
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.production'
    & ./.venv/Scripts/python.exe -m waitress --listen=127.0.0.1:8000 --threads=4 config.wsgi:application
} else {
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.development'
    & ./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
}
if ($LASTEXITCODE -ne 0) { throw 'Falha na inicialização.' }
