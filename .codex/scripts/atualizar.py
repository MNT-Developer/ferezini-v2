"""Valida, migra, coleta estaticos e solicita reinicio ao Passenger."""
import os
import subprocess
import sys
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parents[2]
    ambiente = os.environ.copy()
    ambiente["DJANGO_SETTINGS_MODULE"] = "config.settings"
    ambiente["DJANGO_DEBUG"] = "false"
    subprocess.run([sys.executable, str(raiz / ".codex/scripts/verificar_ambiente.py")],
                   cwd=raiz, env=ambiente, check=True)
    for comando in (["migrate", "--noinput"], ["collectstatic", "--noinput"]):
        subprocess.run([sys.executable, str(raiz / "manage.py"), *comando],
                       cwd=raiz, env=ambiente, check=True)
    pasta = raiz / "tmp"
    pasta.mkdir(mode=0o700, exist_ok=True)
    (pasta / "restart.txt").touch()
    print("Atualizacao concluida. Confirme o reinicio pelo botao Restart do cPanel.")


if __name__ == "__main__":
    main()
