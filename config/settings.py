"""
Configuració del projecte ToDo.

Tota la configuració sensible ve de variables d'entorn (instruccions al README):
  - SECRET_KEY       (obligatòria en producció)
  - DEBUG            (0 en producció; sense env vars cal mode dev automàtic)
  - ALLOWED_HOSTS    (separats per comes, p. ex. "todo.elmeudomini.cat")
  - DATABASE_URL     (p. ex. "postgres://usuari:clau@db:5432/todos")
"""

import os
import sys

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


# Debug: mode desenvolupament apagat per defecte
DEBUG = _env_bool("DEBUG", "0")

# Mode desenvolupament: si no hi ha cap DEBUG ni SECRET_KEY configurats
# (p. ex. `python manage.py runserver` sense res més), mode dev automàtic.
_OPEN_DEBUG = os.environ.get("DEBUG")
_SECRET_KEY = os.environ.get("SECRET_KEY", "")

if _OPEN_DEBUG is None and not _SECRET_KEY:
    DEBUG = True
    SECRET_KEY = "clau-insegura-només-per-a-desenvolupament"
else:
    DEBUG = _env_bool("DEBUG", "0")
    SECRET_KEY = _SECRET_KEY
    if not SECRET_KEY:
        if DEBUG:
            SECRET_KEY = "clau-insegura-només-per-a-desenvolupament"
        else:
            raise ImproperlyConfigured(
                "Defineix la variable d'entorn SECRET_KEY "
                "(obligatòria quan DEBUG=0, p. ex. en producció)."
            )

if SECRET_KEY.startswith("clau-insegura"):
    print(
        "*** Utilitzant una SECRET_KEY insegura per desenvolupament. "
        "Defineix-ne una de real en producció!",
        file=sys.stderr,
    )

# Hostos permesos: p. ex. ALLOWED_HOSTS=todo.elmeudomini.cat
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Orígens de confiança per a CSRF quan l'app viu darrere d'un proxy/domini
# concret: CSRF_TRUSTED_ORIGINS=https://todo.elmeudomini.cat
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tasks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    ),
}

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization

LANGUAGE_CODE = "ca"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Autenticació

LOGIN_REDIRECT_URL = "tasks:list"
LOGOUT_REDIRECT_URL = "login"

# Seguretat en producció (Dokploy serveix l'app darrere d'un proxy HTTPS)
if not DEBUG:
    # El proxy de Dokploy sempre envia aquesta capçalera
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies només per HTTPS: engega COOKIE_SECURE=1 quan serveixis per HTTPS
# (Dokploy amb domini). Off per defecte perquè les proves locals per
# http://localhost funcionin sense configurar res.
if _env_bool("COOKIE_SECURE", "0"):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
