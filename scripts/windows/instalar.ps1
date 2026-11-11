$ErrorActionPreference = 'Stop'
$raizProjeto = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $raizProjeto
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente virtual.' }
& ./.venv/Scripts/python.exe -m pip install -r requirements/windows.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Write-Host 'Configure .env e crie o banco MySQL antes de executar migrate. Consulte README.md para Pango/PDF.'
