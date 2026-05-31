from apps.identity.application.services.authorization_facade import ResourceContext, can_perform
from apps.identity.application.services.role_permission_import import IdentityRolePermissionImportService
from apps.identity.application.services.user_display import get_user_display_map

__all__ = [
    "ResourceContext",
    "can_perform",
    "get_user_display_map",
    "get_role_permission_summary_for_study",
    "import_role_permissions_for_study",
]


def import_role_permissions_for_study(*, study_id: int, import_file):
    return IdentityRolePermissionImportService().import_workbook(study_id=study_id, import_file=import_file)


def get_role_permission_summary_for_study(*, study_id: int):
    return IdentityRolePermissionImportService().build_summary(study_id=study_id)
