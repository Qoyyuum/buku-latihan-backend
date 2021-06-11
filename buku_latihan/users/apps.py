from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "buku_latihan.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import buku_latihan.users.signals  # noqa F401
        except ImportError:
            pass
