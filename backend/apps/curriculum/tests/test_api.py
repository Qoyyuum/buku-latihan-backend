import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.curriculum.models import Subject


@pytest.mark.django_db
def test_subjects_read_only_for_students() -> None:
    student = User.objects.create_user(
        username="s", password="pw", role=UserRole.STUDENT
    )
    Subject.objects.create(name="Mathematics")

    client = APIClient()
    client.force_authenticate(student)

    assert client.get("/api/v1/subjects/").status_code == 200
    assert client.post("/api/v1/subjects/", {"name": "X"}).status_code == 403


@pytest.mark.django_db
def test_teacher_can_create_subject() -> None:
    teacher = User.objects.create_user(
        username="t", password="pw", role=UserRole.TEACHER
    )
    client = APIClient()
    client.force_authenticate(teacher)

    res = client.post("/api/v1/subjects/", {"name": "Physics"})
    assert res.status_code == 201
