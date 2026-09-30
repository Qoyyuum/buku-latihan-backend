from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import (
    ClassroomViewSet,
    EnrollmentViewSet,
    ParentChildViewSet,
    UserViewSet,
)
from apps.curriculum.api.views import SubjectViewSet, TopicViewSet
from apps.submissions.api.views import AttemptViewSet, DashboardView, MarkViewSet
from apps.worksheets.api.views import WorksheetViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("parent-links", ParentChildViewSet, basename="parent-child")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("topics", TopicViewSet, basename="topic")
router.register("worksheets", WorksheetViewSet, basename="worksheet")
router.register("attempts", AttemptViewSet, basename="attempt")
router.register("marks", MarkViewSet, basename="mark")

urlpatterns = [
    *router.urls,
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
