from django.contrib import admin

from apps.worksheets.models import AnswerSheet, Worksheet, WorksheetPage


class WorksheetPageInline(admin.TabularInline):
    model = WorksheetPage
    extra = 0


class AnswerSheetInline(admin.TabularInline):
    model = AnswerSheet
    extra = 0


@admin.register(Worksheet)
class WorksheetAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "topic", "exam_year", "status"]
    list_filter = ["status", "subject"]
    search_fields = ["title", "source"]
    inlines = [WorksheetPageInline, AnswerSheetInline]
