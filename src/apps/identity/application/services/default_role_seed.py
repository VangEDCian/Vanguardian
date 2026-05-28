from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import OperationalError, ProgrammingError, transaction
from django.db.models.signals import post_migrate

from apps.identity.application.default_role_permissions import (
    DEFAULT_EDC_PERMISSION_LABELS,
    DEFAULT_EDC_ROLE_GROUPS,
)
from apps.identity.models import Role, RoleScopeLevel  # noqa: DDD022

_DEFAULT_STUDY_ID = 1
_DISPATCH_UID = "identity.default_role_seed"


def register_default_role_seed():
    post_migrate.connect(seed_default_role_permissions, dispatch_uid=_DISPATCH_UID)


def seed_default_role_permissions(*, using, **kwargs):
    try:
        with transaction.atomic(using=using):
            _ensure_edc_permissions(using=using)
            permission_by_code = _edc_permission_by_code(using=using)
            for role_definition in DEFAULT_EDC_ROLE_GROUPS:
                _sync_role_group(
                    role_definition,
                    permission_by_code=permission_by_code,
                    using=using,
                )
    except (OperationalError, ProgrammingError):
        return


def _ensure_edc_permissions(*, using):
    content_type, _ = ContentType.objects.db_manager(using).get_or_create(
        app_label="edc",
        model="permissioncode",
    )
    for permission_code, permission_label in DEFAULT_EDC_PERMISSION_LABELS.items():
        Permission.objects.db_manager(using).update_or_create(
            content_type=content_type,
            codename=permission_code,
            defaults={"name": permission_label},
        )


def _edc_permission_by_code(*, using):
    permissions = (
        Permission.objects.using(using)
        .select_related("content_type")
        .filter(content_type__app_label="edc", codename__in=DEFAULT_EDC_PERMISSION_LABELS)
    )
    return {permission.codename: permission for permission in permissions}


def _sync_role_group(role_definition, *, permission_by_code, using):
    group = _sync_group(role_definition, permission_by_code=permission_by_code, using=using)
    role, _ = Role.objects.db_manager(using).update_or_create(
        study_id=_DEFAULT_STUDY_ID,
        name=role_definition["role_name"],
        defaults={
            "code": role_definition["role_code"],
            "description": "EDC baseline role",
            "scope_level": RoleScopeLevel(role_definition["scope_level"]),
            "is_system_role": True,
            "is_active": True,
        },
    )
    role.groups.set([group])
    role.permissions.set(_permissions_for_role(role_definition, permission_by_code=permission_by_code))


def _sync_group(role_definition, *, permission_by_code, using):
    group, _ = Group.objects.db_manager(using).get_or_create(name=role_definition["group_name"])
    group.permissions.set(_permissions_for_role(role_definition, permission_by_code=permission_by_code))
    return group


def _permissions_for_role(role_definition, *, permission_by_code):
    return [
        permission_by_code[permission_code]
        for permission_code in role_definition["permissions"]
        if permission_code in permission_by_code
    ]
