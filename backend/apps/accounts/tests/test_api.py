import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Classroom, Enrollment, User, UserRole


@pytest.fixture
def teacher(db) -> User:
    return User.objects.create_user(
        username="teacher", password="pw", role=UserRole.TEACHER
    )


@pytest.fixture
def student(db) -> User:
    return User.objects.create_user(
        username="student", password="pw", role=UserRole.STUDENT
    )


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_me_returns_current_user(client: APIClient, student: User) -> None:
    client.force_authenticate(student)
    res = client.get("/api/v1/users/me/")
    assert res.status_code == 200
    assert res.json()["username"] == "student"


@pytest.mark.django_db
def test_student_cannot_create_users(client: APIClient, student: User) -> None:
    client.force_authenticate(student)
    res = client.post(
        "/api/v1/users/",
        {"username": "x", "password": "pw", "role": "student"},
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_teacher_sees_only_their_students(
    client: APIClient, teacher: User, student: User
) -> None:
    classroom = Classroom.objects.create(name="C1", teacher=teacher)
    Enrollment.objects.create(student=student, classroom=classroom)
    User.objects.create_user(username="other", password="pw")

    client.force_authenticate(teacher)
    res = client.get("/api/v1/users/")
    assert res.status_code == 200
    usernames = {u["username"] for u in res.json()["results"]}
    assert usernames == {"student"}


@pytest.mark.django_db
def test_delete_me_wrong_password(client: APIClient, student: User) -> None:
    client.force_authenticate(student)
    res = client.delete("/api/v1/users/me/", {"password": "nope"}, format="json")
    assert res.status_code == 400
    assert User.objects.filter(pk=student.pk).exists()


@pytest.mark.django_db
def test_delete_me_missing_password(client: APIClient, student: User) -> None:
    client.force_authenticate(student)
    res = client.delete("/api/v1/users/me/", {}, format="json")
    assert res.status_code == 400
    assert User.objects.filter(pk=student.pk).exists()


@pytest.mark.django_db
def test_delete_me_success_cascades(
    client: APIClient, teacher: User, student: User
) -> None:
    classroom = Classroom.objects.create(name="C", teacher=teacher)
    Enrollment.objects.create(student=student, classroom=classroom)
    client.force_authenticate(student)
    res = client.delete("/api/v1/users/me/", {"password": "pw"}, format="json")
    assert res.status_code == 204
    assert not User.objects.filter(pk=student.pk).exists()
    assert not Enrollment.objects.filter(student_id=student.pk).exists()
    assert Classroom.objects.filter(pk=classroom.pk).exists()
    assert User.objects.filter(pk=teacher.pk).exists()


@pytest.mark.django_db
def test_delete_me_unauthenticated(client: APIClient) -> None:
    assert client.delete("/api/v1/users/me/").status_code == 401
