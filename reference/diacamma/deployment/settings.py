"""Use the upstream Lucterios settings factory and module dependencies."""
import os
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

from lucterios.framework.settings import fill_appli_settings

DATA_DIR = Path(os.environ.get("SYNDIC_DATA_DIR", ".local-data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
LANGUAGE_CODE = "fr"
TIME_ZONE = "Europe/Paris"
MEDIA_ROOT = str(DATA_DIR / "media")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
    "LOCATION": str(DATA_DIR / "cache"),
}}

if os.environ.get("POSTGRES_HOST"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "NAME": os.environ.get("POSTGRES_DB", "syndic"),
        "USER": os.environ.get("POSTGRES_USER", "syndic"),
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
    }}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATA_DIR / "db.sqlite3"),
    }}


def linked_modules(application):
    """Resolve the same link() declarations used by lucterios_admin."""
    result = []

    def visit(name):
        if name in result or name == application:
            return
        result.append(name)
        for dependency in getattr(import_module(name), "link", lambda: [])():
            visit(dependency)

    for name in import_module(application).link():
        visit(name)
    return tuple(result)


fill_appli_settings("diacamma.syndic", linked_modules("diacamma.syndic"))

# The upstream factory points these paths into the settings package. Runtime
# artifacts belong in the writable volume, not among application sources.
STATIC_ROOT = str(DATA_DIR / "static")
STATICFILES_DIRS = ()
CACHES["default"]["LOCATION"] = str(DATA_DIR / "cache")
BASE_DIR = str(DATA_DIR)
# Lucterios derives plugin and temporary paths from the instance settings path.
INSTANCE_DIR = DATA_DIR / "deployment"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
SETUP = SimpleNamespace(__file__=str(INSTANCE_DIR / "settings.py"))
MIDDLEWARE = ("whitenoise.middleware.WhiteNoiseMiddleware",) + MIDDLEWARE
