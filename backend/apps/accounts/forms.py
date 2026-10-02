from django import forms

from apps.accounts.models import User, UserRole


class RoleSignupForm(forms.Form):
    """Extra signup field: public registration is student/parent only."""

    role = forms.ChoiceField(
        choices=[
            (UserRole.STUDENT, UserRole.STUDENT.label),
            (UserRole.PARENT, UserRole.PARENT.label),
        ],
    )

    def signup(self, request: object, user: User) -> None:
        user.role = self.cleaned_data["role"]
        user.save(update_fields=["role"])
