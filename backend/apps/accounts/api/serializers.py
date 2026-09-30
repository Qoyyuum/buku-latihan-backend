from typing import Any

from rest_framework import serializers

from apps.accounts.models import Classroom, Enrollment, ParentChild, User, UserRole


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role"]
        read_only_fields = ["id"]


class CreateUserSerializer(serializers.ModelSerializer[User]):
    """Teachers create student/parent accounts — no public signup."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password",
        ]
        read_only_fields = ["id"]

    def validate_role(self, value: str) -> str:
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("Cannot create admin accounts here.")
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EnrollmentSerializer(serializers.ModelSerializer[Enrollment]):
    student = UserSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=UserRole.STUDENT),
        source="student",
        write_only=True,
    )

    class Meta:
        model = Enrollment
        fields = ["id", "student", "student_id", "classroom", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class ClassroomSerializer(serializers.ModelSerializer[Classroom]):
    teacher = UserSerializer(read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)

    class Meta:
        model = Classroom
        fields = ["id", "name", "teacher", "enrollments", "created_at"]
        read_only_fields = ["id", "created_at"]


class ParentChildSerializer(serializers.ModelSerializer[ParentChild]):
    parent = UserSerializer(read_only=True)
    child = UserSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=UserRole.PARENT),
        source="parent",
        write_only=True,
    )
    child_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=UserRole.STUDENT),
        source="child",
        write_only=True,
    )

    class Meta:
        model = ParentChild
        fields = ["id", "parent", "child", "parent_id", "child_id"]
        read_only_fields = ["id"]
