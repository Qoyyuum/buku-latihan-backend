import re

import pytest
from django.core import mail
from django.test import override_settings
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


@pytest.mark.django_db
@override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
def test_signup_mandatory_verification_pending_flow(client: APIClient) -> None:
    res = client.post(
        SIGNUP,
        {
            "username": "ver",
            "email": "ver@x.com",
            "password": "Str0ng!Pass",
            "role": "student",
        },
        format="json",
    )
    # Account is created but unverified: 401 with a pending verify_email flow
    assert res.status_code == 401
    flows = res.json()["data"]["flows"]
    assert any(f["id"] == "verify_email" for f in flows)
    assert User.objects.filter(username="ver").exists()
    assert len(mail.outbox) >= 1


@pytest.mark.django_db
def test_password_reset_roundtrip(client: APIClient, student: User) -> None:
    res = client.post(
        "/_allauth/app/v1/auth/password/request",
        {"email": "student@example.com"},
        format="json",
    )
    assert res.status_code in (200, 401)
    assert len(mail.outbox) >= 1
    match = re.search(r"key=([^\s>\"']+)", mail.outbox[-1].body)
    assert match, mail.outbox[-1].body
    res = client.post(
        "/_allauth/app/v1/auth/password/reset",
        {"key": match.group(1), "password": "N3w!Pass99"},
        format="json",
    )
    # Headless reset succeeds but reports 401 — the user is simply not
    # logged in afterwards and must authenticate with the new password.
    assert res.status_code == 401
    assert "errors" not in res.json()
    student.refresh_from_db()
    assert student.check_password("N3w!Pass99")
    res = client.post(
        LOGIN, {"username": "student", "password": "N3w!Pass99"}, format="json"
    )
    assert res.status_code == 200


@pytest.mark.django_db
def test_cors_preflight_allows_session_token(client: APIClient) -> None:
    res = client.options(
        "/_allauth/app/v1/auth/session",
        HTTP_ORIGIN="http://localhost:4321",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="DELETE",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-session-token",
    )
    assert "x-session-token" in res["access-control-allow-headers"].lower()
