import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
# O instalador opcional mantém as DLLs oficiais isoladas no ambiente virtual.
NATIVE_PDF_DIR = BASE_DIR / ".venv" / "weasyprint-native" / "onedir" / "weasyprint" / "_internal"
if os.name == "nt" and (NATIVE_PDF_DIR / "libpango-1.0-0.dll").is_file():
    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(NATIVE_PDF_DIR))
    if (BASE_DIR / ".venv" / "cache").is_dir():
        os.environ.setdefault("XDG_CACHE_HOME", str(BASE_DIR / ".venv" / "cache"))
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = [v.strip() for v in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",") if v.strip()]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "apps.core", "apps.accounts.apps.AccountsConfig",
    "apps.projetos", "apps.orcamentos", "apps.despesas", "apps.auditoria",
    "apps.envios", "apps.relatorios",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "apps.accounts.context_processors.permissoes",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
AUTH_USER_MODEL = "accounts.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.mysql", "NAME": os.getenv("DB_NAME", "ferezini"),
    "USER": os.getenv("DB_USER", "ferezini"), "PASSWORD": os.getenv("DB_PASSWORD", ""),
    "HOST": os.getenv("DB_HOST", "127.0.0.1"), "PORT": os.getenv("DB_PORT", "3306"),
    "CONN_MAX_AGE": 60,
    "OPTIONS": {"charset": "utf8mb4", "isolation_level": "read committed",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION', default_storage_engine=INNODB"},
    "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
}}
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "login"
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Ferezini <nao-responda@localhost>")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
LOGGING = {"version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"}}
