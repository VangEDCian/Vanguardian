from apps.identity.application.authorization import (
    AuthorizationContext,
    AuthorizationDecision,
    ContextualAuthorizationService,
    user_bypasses_context_permission,
)
from apps.identity.application.services.authorization_facade import ResourceContext, can_perform
from apps.identity.application.services.role_permission_import import IdentityRolePermissionImportService
from apps.identity.application.services.role_scope import IdentityRoleScopeService
from apps.identity.application.services.user_display import get_user_display_map

__all__ = [
    "AuthorizationContext",
    "AuthorizationDecision",
    "ContextualAuthorizationService",
    "ResourceContext",
    "can_perform",
    "create_role_for_study",
    "get_user_display_map",
    "get_role_permission_summary_for_study",
    "get_role_create_options",
    "import_role_permissions_for_study",
    "list_role_options_for_study",
    "user_has_any_active_role_ids",
    "user_bypasses_context_permission",
]


def import_role_permissions_for_study(*, study_id: int, import_file):
    return IdentityRolePermissionImportService().import_workbook(study_id=study_id, import_file=import_file)


def get_role_permission_summary_for_study(*, study_id: int):
    return IdentityRolePermissionImportService().build_summary(study_id=study_id)


def get_role_create_options():
    return IdentityRolePermissionImportService().build_role_create_options()


def create_role_for_study(*, study_id: int, role_data):
    return IdentityRolePermissionImportService().create_role(study_id=study_id, **role_data)


def list_role_options_for_study(*, study_id: int) -> list[dict]:
    return IdentityRoleScopeService().list_study_role_options(study_id=study_id)


def user_has_any_active_role_ids(
    *,
    user_id: int,
    study_id: int,
    site_id: int | None,
    role_ids: tuple[int, ...],
) -> bool:
    return IdentityRoleScopeService().user_has_any_active_role_ids(
        user_id=user_id,
        study_id=study_id,
        site_id=site_id,
        role_ids=role_ids,
    )
