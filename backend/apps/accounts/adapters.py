from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest

from apps.accounts.models import User


class AccountAdapter(DefaultAccountAdapter):
    """Applies the whitelisted `role` chosen at public signup."""

    def save_user(
        self, request: HttpRequest, user: User, form: object, commit: bool = True
    ) -> User:
        user = super().save_user(request, user, form, commit=False)
        role = getattr(form, "cleaned_data", {}).get("role")
        if role:
            user.role = role
        if commit:
            user.save()
        return user
