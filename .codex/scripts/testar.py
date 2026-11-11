"""Executa testes locais ou MySQL em banco temporario exclusivo."""
import argparse
import os
import sys
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql", action="store_true")
    parser.add_argument("--pdf-real", action="store_true")
    parser.add_argument("alvos", nargs="*")
    args = parser.parse_args()
    raiz = Path(__file__).resolve().parents[2]
    os.chdir(raiz)
    sys.path.insert(0, str(raiz))
    sys.path.insert(0, str(raiz / ".codex"))
    os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"
    os.environ["TEST_MYSQL"] = "true" if args.mysql else "false"
    os.environ["TEST_PDF_REAL"] = "true" if args.pdf_real else "false"
    if args.mysql:
        os.environ["TEST_DB_NAME"] = "test_frz_" + uuid.uuid4().hex[:16]
    import django
    django.setup()
    if args.mysql:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s",
                [os.environ["TEST_DB_NAME"]],
            )
            if cursor.fetchone():
                raise RuntimeError("Banco de teste ja existente; operacao cancelada.")
    from django.core.management import call_command
    call_command("test", *(args.alvos or ["apps", "tests_deploy"]), interactive=False)


if __name__ == "__main__":
    main()
