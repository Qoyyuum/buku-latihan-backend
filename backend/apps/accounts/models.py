from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = "admin", _("Admin")
    TEACHER = "teacher", _("Teacher")
    STUDENT = "student", _("Student")
    PARENT = "parent", _("Parent")


class User(AbstractUser):
    """A single user type with a role, rather than separate profile models."""

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )

    class Meta:
        ordering = ["id"]

    @property
    def is_teacher(self) -> bool:
        return self.role in {UserRole.ADMIN, UserRole.TEACHER}

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    @property
    def is_parent(self) -> bool:
        return self.role == UserRole.PARENT


class Classroom(models.Model):
    """A teacher's group of students (a tuition class, a form class, etc.)."""

    name = models.CharField(max_length=120)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="classrooms",
        limit_choices_to={"role__in": [UserRole.ADMIN, UserRole.TEACHER]},
    )
    students = models.ManyToManyField(
        User,
        through="Enrollment",
        related_name="enrolled_classrooms",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": UserRole.STUDENT},
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "classroom"],
                name="unique_enrollment",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student} in {self.classroom}"


class ParentChild(models.Model):
    """Gives a parent read-only visibility over their child's progress."""

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="children",
        limit_choices_to={"role": UserRole.PARENT},
    )
    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="parents",
        limit_choices_to={"role": UserRole.STUDENT},
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "child"],
                name="unique_parent_child",
            )
        ]
        verbose_name_plural = "parent-child links"

    def __str__(self) -> str:
        return f"{self.parent} -> {self.child}"
