from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.identity.infrastructure.persistence.models import Role, RoleGroup, RolePermission, User


@admin.register(User)
class IdentityUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone_number", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone_number", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("phone_number",)}),
    )


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
