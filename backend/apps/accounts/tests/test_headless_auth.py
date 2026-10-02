import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole

SIGNUP = "/_allauth/app/v1/auth/signup"
LOGIN = "/_allauth/app/v1/auth/login"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def student(db) -> User:
    return User.objects.create_user(
        username="student",
        password="pw",
        role=UserRole.STUDENT,
        email="student@example.com",
    )


@pytest.mark.django_db
def test_signup_student(client: APIClient) -> None:
    res = client.post(
        SIGNUP,
        {
            "username": "new",
            "email": "n@x.com",
            "password": "Str0ng!Pass",
            "role": "student",
        },
        format="json",
    )
    assert res.status_code == 200
    assert User.objects.get(username="new").role == UserRole.STUDENT


@pytest.mark.django_db
def test_signup_parent_gets_parent_role(client: APIClient) -> None:
    res = client.post(
        SIGNUP,
        {
            "username": "mom",
            "email": "mom@x.com",
            "password": "Str0ng!Pass",
            "role": "parent",
        },
        format="json",
    )
    assert res.status_code == 200
    assert User.objects.get(username="mom").role == UserRole.PARENT


@pytest.mark.django_db
def test_signup_teacher_rejected(client: APIClient) -> None:
    res = client.post(
        SIGNUP,
        {
            "username": "t",
            "email": "t@x.com",
            "password": "Str0ng!Pass",
            "role": "teacher",
        },
        format="json",
    )
    assert res.status_code in (400, 403)
    assert not User.objects.filter(username="t").exists()


@pytest.mark.django_db
def test_signup_admin_rejected(client: APIClient) -> None:
    res = client.post(
        SIGNUP,
        {
            "username": "a",
            "email": "a@x.com",
            "password": "Str0ng!Pass",
            "role": "admin",
        },
        format="json",
    )
    assert res.status_code in (400, 403)
    assert not User.objects.filter(username="a").exists()


@pytest.mark.django_db
def test_login_returns_session_token(client: APIClient, student: User) -> None:
    res = client.post(
        LOGIN,
        {"username": "student", "password": "pw"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["session_token"]


@pytest.mark.django_db
def test_jwt_login_still_works(client: APIClient, student: User) -> None:
    res = client.post(
        "/api/v1/auth/token/",
        {"username": "student", "password": "pw"},
        format="json",
    )
    assert res.status_code == 200
    assert "access" in res.json()
