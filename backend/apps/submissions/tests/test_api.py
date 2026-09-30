import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.curriculum.models import Subject
from apps.submissions.models import Attempt, AttemptStatus
from apps.worksheets.models import Worksheet, WorksheetStatus


@pytest.fixture
def worksheet(db) -> Worksheet:
    return Worksheet.objects.create(
        subject=Subject.objects.create(name="Math"),
        title="Paper 1",
        status=WorksheetStatus.PUBLISHED,
    )


@pytest.mark.django_db
def test_attempt_visibility_scoped_to_owner(worksheet: Worksheet) -> None:
    s1 = User.objects.create_user(username="s1", password="pw")
    s2 = User.objects.create_user(username="s2", password="pw")
    Attempt.objects.create(student=s1, worksheet=worksheet)
    Attempt.objects.create(student=s2, worksheet=worksheet)

    client = APIClient()
    client.force_authenticate(s1)
    res = client.get("/api/v1/attempts/")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


@pytest.mark.django_db
def test_create_attempt_reuses_in_progress(worksheet: Worksheet) -> None:
    student = User.objects.create_user(username="s", password="pw")
    client = APIClient()
    client.force_authenticate(student)

    res1 = client.post("/api/v1/attempts/", {"worksheet_id": worksheet.pk})
    res2 = client.post("/api/v1/attempts/", {"worksheet_id": worksheet.pk})
    assert res1.status_code == 201
    assert res1.json()["id"] == res2.json()["id"]
    assert (
        Attempt.objects.filter(
            student=student, status=AttemptStatus.IN_PROGRESS
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_dashboard_returns_stats(worksheet: Worksheet) -> None:
    student = User.objects.create_user(username="s", password="pw")
    Attempt.objects.create(student=student, worksheet=worksheet)

    client = APIClient()
    client.force_authenticate(student)
    res = client.get("/api/v1/dashboard/")
    assert res.status_code == 200
    body = res.json()
    assert body["attempts_total"] == 1
    assert body["attempts_by_status"]["in_progress"] == 1
