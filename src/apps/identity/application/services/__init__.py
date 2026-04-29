from importlib import import_module

__all__ = [
    "CreateIdentityUserService",
    "DeleteIdentityUserService",
    "IdentityLoginAuditService",
    "IdentityUserAuditService",
    "IdentityUserDirectoryQueryService",
    "IdentityUserFilterActiveQueryService",
    "IdentityUserFilterInactiveQueryService",
    "IdentityUserNotFoundError",
    "RestoreIdentityUserService",
    "UpdateIdentityUserDetailService",
    "serialize_identity_user_snapshot",
]

_MODULE_BY_NAME = {
    "CreateIdentityUserService": "apps.identity.application.services.create_user",
    "DeleteIdentityUserService": "apps.identity.application.services.delete_user",
    "IdentityLoginAuditService": "apps.identity.application.services.login_audit",
    "IdentityUserAuditService": "apps.identity.application.services.user_audit",
    "IdentityUserDirectoryQueryService": "apps.identity.application.services.user_directory",
    "IdentityUserFilterActiveQueryService": "apps.identity.application.services.user_filters",
    "IdentityUserFilterInactiveQueryService": "apps.identity.application.services.user_filters",
    "IdentityUserNotFoundError": "apps.identity.application.services.user_directory",
    "RestoreIdentityUserService": "apps.identity.application.services.delete_user",
    "UpdateIdentityUserDetailService": "apps.identity.application.services.update_user_detail",
    "serialize_identity_user_snapshot": "apps.identity.application.services.user_audit",
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
