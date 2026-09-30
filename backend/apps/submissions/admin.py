from django.contrib import admin

from apps.submissions.models import Attempt, GradeJob, Mark, PageSubmission


class PageSubmissionInline(admin.TabularInline):
    model = PageSubmission
    extra = 0


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["student", "worksheet", "status", "started_at", "submitted_at"]
    list_filter = ["status", "worksheet__subject"]
    inlines = [PageSubmissionInline]


@admin.register(GradeJob)
class GradeJobAdmin(admin.ModelAdmin):
    list_display = ["id", "attempt", "status", "created_at", "finished_at"]
    list_filter = ["status"]


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ["attempt", "score", "max_score", "auto_suggested", "marked_by"]
