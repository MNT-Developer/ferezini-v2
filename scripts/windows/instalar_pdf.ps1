$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$codigoPdf = @'
from pathlib import Path
import hashlib
import io
import urllib.request
import zipfile

url = 'https://github.com/Kozea/WeasyPrint/releases/download/v70.0/weasyprint-windows-onedir.zip'
esperado = 'ab1151f210b4e6bb7aa7a79e91a67e8ddb760094c107bfda55241b6aaefe7d53'
conteudo = urllib.request.urlopen(url, timeout=60).read()
if hashlib.sha256(conteudo).hexdigest() != esperado:
    raise RuntimeError('O checksum do pacote oficial nao confere; instalacao interrompida.')
destino = Path('.venv/weasyprint-native').resolve()
destino.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
    for arquivo in pacote.infolist():
        if not (destino / arquivo.filename).resolve().is_relative_to(destino):
            raise RuntimeError('Caminho inseguro no pacote; instalacao interrompida.')
    pacote.extractall(destino)
Path('.venv/cache').mkdir(exist_ok=True)
print('Bibliotecas oficiais WeasyPrint 70.0 instaladas somente na .venv do projeto.')
'@
& ./.venv/Scripts/python.exe -c $codigoPdf
if ($LASTEXITCODE -ne 0) { throw 'Falha na instalação local das bibliotecas PDF.' }
Write-Host 'A configuração Django detecta essas DLLs automaticamente. Alternativa: Pango via MSYS2, conforme README.md.'
