"""Entrada curta para Cron do cPanel; usa a fila e os bloqueios persistentes."""
import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=1)
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("O limite deve ser positivo.")
    raiz = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(raiz))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["DJANGO_DEBUG"] = "false"
    import django
    django.setup()
    from django.core.management import call_command
    call_command("processar_emails_pendentes", limite=args.limite)


if __name__ == "__main__":
    main()
