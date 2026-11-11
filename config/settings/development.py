from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "desenvolvimento-local-nao-usar-em-producao"  # noqa: F405
# SQLite é opt-in apenas para demonstração/testes; a configuração padrão usa MySQL.
if os.getenv("DB_ENGINE") == "sqlite":  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}  # noqa: F405
