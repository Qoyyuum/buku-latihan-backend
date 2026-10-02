"""
Base settings for Buku Latihan.

Shared across all environments. Environment-specific overrides live in
``local.py``, ``production.py`` and ``test.py``.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env.read_env(BASE_DIR / ".env")

# ------------------------------------------------------------------------------
# Core
# ------------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)
TIME_ZONE = "UTC"
USE_TZ = True
LANGUAGE_CODE = "en-us"
USE_I18N = True
SITE_ID = 1

# ------------------------------------------------------------------------------
# Applications
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.mfa",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "storages",
]
LOCAL_APPS = [
    "apps.accounts",
    "apps.curriculum",
    "apps.worksheets",
    "apps.submissions",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

# ------------------------------------------------------------------------------
# Middleware / URLs / Templates
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------------------------
# Database
# ------------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------------------
# Auth / passwords
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------------------
# Static / media
# ------------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------------------------------------------------------
# CORS — the Expo web build and admin dashboard call this API cross-origin
# ------------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:8081", "http://127.0.0.1:8081"],
)

# Required for admin/forms over HTTPS behind a reverse proxy.
CSRF_TRUSTED_ORIGINS: list[str] = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8081", "http://127.0.0.1:8081"],
)

# ------------------------------------------------------------------------------
# DRF
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "allauth.headless.contrib.rest_framework.authentication.XSessionTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Buku Latihan API",
    "DESCRIPTION": (
        "Practice past-year papers and exercises — write on worksheets "
        "with a stylus, get marked by teachers."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ------------------------------------------------------------------------------
# django-allauth (headless account portal auth)
# ------------------------------------------------------------------------------
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:4321")

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env(
    "ACCOUNT_EMAIL_VERIFICATION", default="mandatory"
)
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
ACCOUNT_SIGNUP_FORM_CLASS = "apps.accounts.forms.RoleSignupForm"

HEADLESS_CLIENTS = ["app"]
HEADLESS_ONLY = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{FRONTEND_BASE_URL}/verify-email?key={{key}}",
    "account_reset_password_from_key": (
        f"{FRONTEND_BASE_URL}/reset-password?key={{key}}"
    ),
    "account_signup": f"{FRONTEND_BASE_URL}/signup",
}

# ------------------------------------------------------------------------------
# Email — console locally, SMTP via env in production
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@bukulatihan.app")

# ------------------------------------------------------------------------------
# Celery
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_TASK_TRACK_STARTED = True

# ------------------------------------------------------------------------------
# Object storage (S3-compatible: Cloudflare R2 in prod, MinIO locally)
# ------------------------------------------------------------------------------
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="buku-latihan-media")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://localhost:9000")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="auto")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_QUERYSTRING_AUTH = False  # use presigned URLs we generate ourselves
AWS_DEFAULT_ACL = None

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Presigned URL lifetime for worksheet bundle downloads
WORKSHEET_URL_TTL_SECONDS = env.int("WORKSHEET_URL_TTL_SECONDS", default=86400)

# ------------------------------------------------------------------------------
# OpenRouter — grading pipeline
# ------------------------------------------------------------------------------
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")
OPENROUTER_BASE_URL = env("OPENROUTER_BASE_URL", default="https://openrouter.ai/api")
OPENROUTER_TRANSCRIBE_MODEL = env(
    "OPENROUTER_TRANSCRIBE_MODEL",
    default="openrouter/free",
)
OPENROUTER_GRADE_MODEL = env("OPENROUTER_GRADE_MODEL", default="typesafe/jev-1.13")
OPENROUTER_HTTP_REFERER = env("OPENROUTER_HTTP_REFERER", default="")
OPENROUTER_APP_NAME = env("OPENROUTER_APP_NAME", default="buku-latihan")
