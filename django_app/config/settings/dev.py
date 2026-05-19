from .base import *  # noqa: F403


DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSP_REPORT_ONLY = True

# Em dev/testes não rodamos collectstatic, então usamos storage simples sem manifesto
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
