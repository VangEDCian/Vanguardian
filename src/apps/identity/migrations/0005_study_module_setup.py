"""
State + data migration: set up all study-module related identity state in one step.

Schema state (no DB ops — all tables are managed=False / DB-first):
  - Register Role, RoleGroup, RolePermission models
  - Update User model options
  - Update StudyMembership and StudySiteMembership to final schema

Data:
  - Seed Administrator and Data Manager roles
  - Grant all study permissions to each role according to their scope
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.contrib.auth.models import Permission


# ---------------------------------------------------------------------------
# Permission lists
# ---------------------------------------------------------------------------

ADMIN_PERMS = [
    "view_study_list",
    "view_study_detail",
    "view_study_history",
    "create_study",
    "update_study",
    "change_study_status",
    "delete_study",
    "search_study_by_name",
    "filter_study_by_code",
    "filter_study_by_status",
    "view_study_field_code",
    "view_study_field_name",
    "view_study_field_sponsor",
    "view_study_field_dates",
    "view_study_field_description",
    "update_study_field_code",
    "update_study_field_name",
    "update_study_field_sponsor",
    "update_study_field_dates",
    "update_study_field_description",
]

DATA_MANAGER_PERMS = [
    "view_study_list",
    "view_study_detail",
    "view_study_history",
    "update_study",
    "search_study_by_name",
    "filter_study_by_code",
    "filter_study_by_status",
    "view_study_field_code",
    "view_study_field_name",
    "view_study_field_sponsor",
    "view_study_field_dates",
    "view_study_field_description",
    # update_study_field_code excluded — Data Manager cannot change study code
    "update_study_field_name",
    "update_study_field_sponsor",
    "update_study_field_dates",
    "update_study_field_description",
]


# ---------------------------------------------------------------------------
# Data migration functions
# ---------------------------------------------------------------------------

def seed_roles_and_permissions(apps, schema_editor):
    # Import real model classes: safe because these are managed=False (schema fixed).
    from apps.identity.infrastructure.persistence.models import Role, RolePermission

    administrator, _ = Role.objects.get_or_create(
        name="Administrator",
        defaults={"description": "Full access to all system operations."},
    )
    data_manager, _ = Role.objects.get_or_create(
        name="Data Manager",
        defaults={"description": "Read and update studies within assigned scope."},
    )

    def _grant(role, codenames):
        for codename in codenames:
            try:
                perm = Permission.objects.get(codename=codename, content_type__app_label="study")
            except Permission.DoesNotExist:
                continue
            RolePermission.objects.get_or_create(role=role, permission=perm)

    _grant(administrator, ADMIN_PERMS)
    _grant(data_manager, DATA_MANAGER_PERMS)


def unseed_roles_and_permissions(apps, schema_editor):
    from apps.identity.infrastructure.persistence.models import Role
    Role.objects.filter(name__in=["Administrator", "Data Manager"]).delete()


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0004_membership_state"),
        ("study", "0001_study_state"),
    ]

    operations = [
        # ── Schema state: Role, RoleGroup, RolePermission, User options ─────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Role",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=150, unique=True)),
                        ("description", models.CharField(blank=True, default="", max_length=255)),
                    ],
                    options={
                        "verbose_name": "role",
                        "verbose_name_plural": "roles",
                        "db_table": "identity_role",
                        "managed": False,
                        "default_permissions": (),
                    },
                ),
                migrations.CreateModel(
                    name="RoleGroup",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ],
                    options={
                        "verbose_name": "role group mapping",
                        "verbose_name_plural": "role group mappings",
                        "db_table": "identity_role_groups",
                        "permissions": (),
                        "managed": False,
                        "default_permissions": (),
                    },
                ),
                migrations.CreateModel(
                    name="RolePermission",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ],
                    options={
                        "verbose_name": "role permission mapping",
                        "verbose_name_plural": "role permission mappings",
                        "db_table": "identity_role_permissions",
                        "permissions": (),
                        "managed": False,
                        "default_permissions": (),
                    },
                ),
                migrations.AlterModelOptions(
                    name="user",
                    options={"default_permissions": (), "managed": False, "verbose_name": "user", "verbose_name_plural": "users"},
                ),
            ],
        ),
        # ── Schema state: StudyMembership and StudySiteMembership ────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="StudyMembership"),
                migrations.DeleteModel(name="StudySiteMembership"),
                migrations.CreateModel(
                    name="StudyMembership",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("user", models.ForeignKey(
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="study_memberships",
                            to=settings.AUTH_USER_MODEL,
                        )),
                        ("study_id", models.BigIntegerField()),
                        ("role", models.CharField(max_length=64)),
                        ("is_global_role", models.BooleanField(default=False)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                    ],
                    options={
                        "verbose_name": "study membership",
                        "verbose_name_plural": "study memberships",
                        "db_table": "study_membership",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (),
                        "unique_together": {("user", "study_id")},
                    },
                ),
                migrations.CreateModel(
                    name="StudySiteMembership",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("user", models.ForeignKey(
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="study_site_memberships",
                            to=settings.AUTH_USER_MODEL,
                        )),
                        ("study_id", models.BigIntegerField()),
                        ("site_id", models.BigIntegerField()),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                    ],
                    options={
                        "verbose_name": "study site membership",
                        "verbose_name_plural": "study site memberships",
                        "db_table": "study_site_membership",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (),
                        "unique_together": {("user", "study_id", "site_id")},
                    },
                ),
            ],
        ),
        # ── Data: seed roles and grant permissions ───────────────────────────
        migrations.RunPython(seed_roles_and_permissions, reverse_code=unseed_roles_and_permissions),
    ]
