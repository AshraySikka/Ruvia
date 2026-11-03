"""Ruvia backend settings. Every secret comes from environment variables."""
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = env("SECRET_KEY") or ("dev-only-insecure-key-change-me-before-deploying-0000" if DEBUG else None)
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is required when DEBUG is off.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "accounts",
    "health",
    "care",
    "notify",
    "assistant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(env("DB_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-ca"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/hour", "user": "2000/hour", "chat": "60/hour"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "30"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_URL)
if DEBUG:
    CORS_ALLOWED_ORIGINS += ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"]
if env("CORS_ALLOWED_ORIGIN_REGEX"):
    CORS_ALLOWED_ORIGIN_REGEXES = [env("CORS_ALLOWED_ORIGIN_REGEX")]
CSRF_TRUSTED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if o.startswith("https://")]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Field level encryption for free text (check-ins, notes). Generate with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", "")
if not FIELD_ENCRYPTION_KEY and not DEBUG:
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY is required when DEBUG is off.")

# Email (SendGrid)
SENDGRID_API_KEY = env("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = env("SENDGRID_FROM_EMAIL", "hello@ruvia.app")
SENDGRID_FROM_NAME = env("SENDGRID_FROM_NAME", "Ruvia")

# Language model providers, tried in this order
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TRANSCRIBE_MODEL = env("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
GEMINI_API_KEY = env("GEMINI_API_KEY", "")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", "claude-haiku-5-5")
LLM_TIMEOUT_SECONDS = float(env("LLM_TIMEOUT_SECONDS", "20"))

# Web Push
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = env("VAPID_SUBJECT", "mailto:hello@ruvia.app")

# Shared secret for the scheduler endpoint
CRON_SECRET = env("CRON_SECRET", "")

DEMO_PASSWORD = env("DEMO_PASSWORD", "RuviaDemo2026!")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
