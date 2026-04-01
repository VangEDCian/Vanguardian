from django.contrib import admin

from apps.audit.infrastructure.persistence.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_id", "user", "ip_address", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("action", "object_type", "object_id", "user__username", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at", "updated_at", "action", "object_type", "object_id",
        "before_data", "after_data", "ip_address", "user_agent", "user",
        "created_by", "updated_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
