from .base import *  # noqa: F403

SECRET_KEY = "chave-exclusiva-dos-testes-sem-uso-em-producao"
if os.getenv("TEST_MYSQL", "false").lower() != "true":  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
elif os.getenv("TEST_DB_NAME"):  # noqa: F405
    DATABASES["default"]["TEST"]["NAME"] = os.environ["TEST_DB_NAME"]  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
