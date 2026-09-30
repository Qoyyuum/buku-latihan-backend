import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.curriculum.models import Subject
from apps.worksheets.models import Worksheet, WorksheetStatus


@pytest.fixture
def subject(db) -> Subject:
    return Subject.objects.create(name="Math")


@pytest.mark.django_db
def test_students_see_only_published(subject: Subject) -> None:
    Worksheet.objects.create(
        subject=subject, title="Draft", status=WorksheetStatus.DRAFT
    )
    Worksheet.objects.create(
        subject=subject, title="Published", status=WorksheetStatus.PUBLISHED
    )
    student = User.objects.create_user(
        username="s", password="pw", role=UserRole.STUDENT
    )
    client = APIClient()
    client.force_authenticate(student)

    res = client.get("/api/v1/worksheets/")
    assert res.status_code == 200
    titles = [w["title"] for w in res.json()["results"]]
    assert titles == ["Published"]


@pytest.mark.django_db
def test_teachers_see_all(subject: Subject) -> None:
    Worksheet.objects.create(
        subject=subject, title="Draft", status=WorksheetStatus.DRAFT
    )
    teacher = User.objects.create_user(
        username="t", password="pw", role=UserRole.TEACHER
    )
    client = APIClient()
    client.force_authenticate(teacher)

    res = client.get("/api/v1/worksheets/")
    assert len(res.json()["results"]) == 1
