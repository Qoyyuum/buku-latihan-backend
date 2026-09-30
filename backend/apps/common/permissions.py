from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole


class IsTeacher(BasePermission):
    """Admins count as teachers for permission purposes."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return isinstance(request.user, User) and request.user.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }


class IsStudent(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return isinstance(request.user, User) and request.user.role == UserRole.STUDENT


class IsTeacherOrReadOnly(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not isinstance(request.user, User):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in {UserRole.ADMIN, UserRole.TEACHER}
