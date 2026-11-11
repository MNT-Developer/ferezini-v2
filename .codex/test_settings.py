"""Isolamento dos testes; nao e um segundo ambiente de implantacao."""
import os

os.environ["DJANGO_DEBUG"] = "true"
os.environ["DJANGO_SECRET_KEY"] = "chave-exclusiva-dos-testes-sem-uso-em-producao"
os.environ["DB_ENGINE"] = "mysql"

from config.settings import *  # noqa: E402,F403

DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
if os.getenv("TEST_MYSQL", "false").lower() != "true":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
elif os.getenv("TEST_DB_NAME"):
    DATABASES["default"]["TEST"]["NAME"] = os.environ["TEST_DB_NAME"]  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# A suite comum nao depende de collectstatic; testes de producao validam o manifesto.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
