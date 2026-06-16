from apps.identity.application.authorization import (
    AuthorizationContext,
    AuthorizationDecision,
    ContextualAuthorizationService,
    user_bypasses_context_permission,
)
from apps.identity.application.services.authorization_facade import ResourceContext, can_perform
from apps.identity.application.services.role_permission_import import IdentityRolePermissionImportService
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
