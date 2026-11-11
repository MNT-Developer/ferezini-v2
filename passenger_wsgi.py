"""Entrada WSGI de producao usada pelo Python Selector/Passenger do cPanel."""
import os
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ_PROJETO))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "false"

from config.wsgi import application  # noqa: E402,F401
