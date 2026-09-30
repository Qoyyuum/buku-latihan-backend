from config.settings.base import *  # noqa: F403
from config.settings.base import env

DEBUG = True

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-local-dev-key")

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
