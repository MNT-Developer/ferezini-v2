from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY com pelo menos 50 caracteres em produção.")
if not os.getenv("DJANGO_ALLOWED_HOSTS"):  # noqa: F405
    raise ImproperlyConfigured("Defina DJANGO_ALLOWED_HOSTS em produção.")
if os.getenv("DB_ENGINE") == "sqlite":  # noqa: F405
    raise ImproperlyConfigured("Produção requer MySQL/MariaDB.")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")  # noqa: F405
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Ative somente quando o proxy remover o cabeçalho recebido do cliente e defini-lo.
if os.getenv("TRUST_PROXY_HTTPS", "false").lower() == "true":  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
