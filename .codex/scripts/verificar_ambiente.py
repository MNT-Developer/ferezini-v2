"""Verifica dependencias do FRZ no plano cPanel, sem transmitir e-mails."""
import os
import sys
import tempfile
from pathlib import Path


def verificar():
    if sys.version_info < (3, 11):
        raise SystemExit("Selecione Python 3.11 ou superior no cPanel; prefira 3.12/3.13.")
    raiz = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(raiz))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["DJANGO_DEBUG"] = "false"
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connection
    call_command("check", deploy=True, fail_level="WARNING")
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SHOW ENGINES")
        if not any(linha[0].lower() == "innodb" and linha[1].upper() in {"YES", "DEFAULT"}
                   for linha in cursor.fetchall()):
            raise RuntimeError("O banco precisa de InnoDB para preservar transacoes e bloqueios.")
    cache = Path(os.environ["XDG_CACHE_HOME"])
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=cache):
        pass
    from weasyprint import HTML
    pdf = HTML(string="<html><body><p>FRZ - teste de PDF em memoria</p></body></html>").write_pdf()
    if not pdf.startswith(b"%PDF-"):
        raise RuntimeError("O mecanismo PDF nao retornou um documento valido.")
    print("Python:", sys.version.split()[0], "| Django:", django.get_version())
    print("Banco:", connection.mysql_server_info, "| InnoDB e conexao: OK")
    print("Cache de fontes e PDF em memoria: OK. Nenhum e-mail foi enviado.")


if __name__ == "__main__":
    verificar()
