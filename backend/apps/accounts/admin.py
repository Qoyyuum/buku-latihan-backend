from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import Classroom, Enrollment, ParentChild, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "is_staff"]
    list_filter = ["role", "is_staff"]
    fieldsets = (
        *(BaseUserAdmin.fieldsets or ()),
        ("Buku Latihan", {"fields": ("role",)}),
    )


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ["name", "teacher"]
    search_fields = ["name", "teacher__username"]
    inlines = [EnrollmentInline]


@admin.register(ParentChild)
class ParentChildAdmin(admin.ModelAdmin):
    list_display = ["parent", "child"]
