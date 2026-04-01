from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from apps.identity.infrastructure.persistence.models import (
    Role,
    RoleGroup,
    RolePermission,
    StudyMembership,
    StudySiteMembership,
    User,
)


@admin.register(User)
class IdentityUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone_number", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone_number", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (("Profile", {"fields": ("phone_number",)}),)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(RoleGroup)
class RoleGroupAdmin(admin.ModelAdmin):
    list_display = ("role", "group")
    list_filter = ("role",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")
    list_filter = ("role",)


@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "study_id", "role", "is_global_role", "deleted", "created_at")
    list_filter = ("role", "is_global_role", "deleted")
    search_fields = ("user__username", "user__email")
    ordering = ("study_id", "user")
    readonly_fields = ("created_at", "updated_at", "created_by_id", "updated_by_id")

    def save_model(self, request, obj, form, change):
        now = timezone.now()
        if not change:
            obj.created_at = now
            obj.created_by_id = request.user.pk
        obj.updated_at = now
        obj.updated_by_id = request.user.pk
        super().save_model(request, obj, form, change)


@admin.register(StudySiteMembership)
class StudySiteMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "study_id", "site_id", "deleted", "created_at")
    list_filter = ("deleted",)
    search_fields = ("user__username", "user__email")
    ordering = ("study_id", "site_id", "user")
    readonly_fields = ("created_at", "updated_at", "created_by_id", "updated_by_id")

    def save_model(self, request, obj, form, change):
        now = timezone.now()
        if not change:
            obj.created_at = now
            obj.created_by_id = request.user.pk
        obj.updated_at = now
        obj.updated_by_id = request.user.pk
        super().save_model(request, obj, form, change)
