"""Instala dependencias no virtualenv selecionado pelo cPanel, sem sudo."""
import os
import secrets
import subprocess
import sys
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    if sys.version_info < (3, 11):
        raise SystemExit("Selecione Python 3.11 ou superior no cPanel; prefira 3.12/3.13.")
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Execute este script com o Python do virtualenv fornecido pelo cPanel.")
    if "public_html" in (parte.lower() for parte in raiz.parts):
        raise SystemExit("A raiz da aplicacao deve ficar fora de public_html, protegendo codigo e .env.")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--no-cache-dir",
        "-r", str(raiz / "requirements.txt"),
    ], check=True)
    ambiente = raiz / ".env"
    if not ambiente.exists():
        texto = (raiz / ".codex/.env.example").read_text(encoding="utf-8")
        texto = texto.replace("DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(64) + "\n")
        descriptor = os.open(ambiente, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(texto)
    (raiz / "tmp").mkdir(mode=0o700, exist_ok=True)
    (raiz / ".cache").mkdir(mode=0o700, exist_ok=True)
    print("Dependencias instaladas. Configure o .env com dominio, banco e SMTP da sua conta.")
    print("Depois execute verificar_ambiente.py e atualizar.py com este mesmo Python.")


if __name__ == "__main__":
    main()
