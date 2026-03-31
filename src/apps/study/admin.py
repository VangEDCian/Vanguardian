from django.contrib import admin

from apps.study.infrastructure.persistence.models import Study


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "sponsor", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "sponsor")
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at", "created_by_id", "updated_by_id")
