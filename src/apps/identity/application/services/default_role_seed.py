from django.db import OperationalError, ProgrammingError, transaction

from apps.identity.application.default_role_permissions import (
    DEFAULT_EDC_PERMISSION_LABELS,
    DEFAULT_EDC_ROLES,
)
from apps.identity.application.permissions import EDC_PERMISSION_DEFINITIONS
from apps.identity.models import IdentityPermission, Role, RoleScopeLevel  # noqa: DDD022

_DEFAULT_STUDY_ID = 1


def seed_default_role_permissions(*, using, **kwargs):
    try:
        with transaction.atomic(using=using):
            _ensure_edc_permissions(using=using)
            permission_by_code = _edc_permission_by_code(using=using)
            for role_definition in DEFAULT_EDC_ROLES:
                _sync_role(
                    role_definition,
                    permission_by_code=permission_by_code,
                    using=using,
                )
    except (OperationalError, ProgrammingError):
        return


def _ensure_edc_permissions(*, using):
    for definition in EDC_PERMISSION_DEFINITIONS:
        IdentityPermission.objects.db_manager(using).update_or_create(
            app_label=definition.app_label,
            codename=definition.codename,
            defaults={"name": definition.label},
        )


def _edc_permission_by_code(*, using):
    permissions = (
        IdentityPermission.objects.using(using)
        .filter(app_label="edc", codename__in=DEFAULT_EDC_PERMISSION_LABELS)
    )
    return {permission.codename: permission for permission in permissions}


def _sync_role(role_definition, *, permission_by_code, using):
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
    role.permissions.set(_permissions_for_role(role_definition, permission_by_code=permission_by_code))


def _permissions_for_role(role_definition, *, permission_by_code):
    return [
        permission_by_code[permission_code]
        for permission_code in role_definition["permissions"]
        if permission_code in permission_by_code
    ]
