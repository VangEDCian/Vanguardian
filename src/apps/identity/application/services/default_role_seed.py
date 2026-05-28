from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import OperationalError, ProgrammingError, transaction
from django.db.models.signals import post_migrate

from apps.identity.application.default_role_permissions import (
    DEFAULT_PERMISSION_CONTENT_TYPES,
    DEFAULT_PERMISSION_LABELS,
    DEFAULT_ROLE_GROUPS,
)
from apps.identity.models import Role, RoleScopeLevel  # noqa: DDD022

_DEFAULT_STUDY_ID = 1
_DISPATCH_UID = "identity.default_role_seed"
_SCOPE_LEVEL_BY_DEFAULT_SCOPE = {
    "global": RoleScopeLevel.GLOBAL,
    "study": RoleScopeLevel.STUDY,
    "study_site": RoleScopeLevel.STUDY_SITE,
}


def register_default_role_seed():
    post_migrate.connect(seed_default_role_permissions, dispatch_uid=_DISPATCH_UID)


def seed_default_role_permissions(*, using, **kwargs):
    try:
        with transaction.atomic(using=using):
            _ensure_permissions(using=using)
            permission_by_code = _permission_by_code(using=using)
            for role_definition in DEFAULT_ROLE_GROUPS:
                _sync_role_group(
                    role_definition,
                    permission_by_code=permission_by_code,
                    using=using,
                )
    except (OperationalError, ProgrammingError):
        return


def _ensure_permissions(*, using):
    for permission_code, permission_label in DEFAULT_PERMISSION_LABELS.items():
        app_label, codename = permission_code.split(".", 1)
        model = DEFAULT_PERMISSION_CONTENT_TYPES[app_label]
        content_type, _ = ContentType.objects.db_manager(using).get_or_create(
            app_label=app_label,
            model=model,
        )
        Permission.objects.db_manager(using).update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": permission_label},
        )


def _permission_by_code(*, using):
    permissions = (
        Permission.objects.using(using)
        .select_related("content_type")
        .filter(content_type__app_label__in=DEFAULT_PERMISSION_CONTENT_TYPES)
    )
    return {f"{permission.content_type.app_label}.{permission.codename}": permission for permission in permissions}


def _sync_role_group(role_definition, *, permission_by_code, using):
    group = _sync_group(role_definition, permission_by_code=permission_by_code, using=using)
    role, _ = Role.objects.db_manager(using).update_or_create(
        study_id=_DEFAULT_STUDY_ID,
        name=role_definition["role_name"],
        defaults={
            "code": role_definition["role_code"],
            "description": ", ".join(role_definition.get("access_levels", ())),
            "scope_level": _SCOPE_LEVEL_BY_DEFAULT_SCOPE[role_definition["scope"]],
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
