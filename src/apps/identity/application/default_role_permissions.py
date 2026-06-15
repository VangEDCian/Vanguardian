from apps.identity.application import permissions as permission_registry

DEFAULT_PERMISSION_LABELS = permission_registry.APP_PERMISSION_LABELS
DEFAULT_EDC_PERMISSION_LABELS = permission_registry.EDC_PERMISSION_LABELS
DEFAULT_PERMISSION_CONTENT_TYPES = {
    "dashboard": "dashboard",
    "identity": "user",
    "reconcile": "dataquery",
    "site": "site",
    "study": "study",
    "subject": "subject",
}

DEFAULT_EDC_ROLES = (
    {
        "role_code": "PI",
        "role_name": "PI",
        "scope_level": "STUDY_SITE",
        "permissions": (
            "SUBJECT.VIEW",
            "CRF.VIEW",
            "QUERY.VIEW",
            "CASEBOOK.VIEW",
            "CASEBOOK.SIGN",
            "DELEGATION.VIEW",
            "DELEGATION.MANAGE",
        ),
    },
    {
        "role_code": "SITE_COORDINATOR",
        "role_name": "Site Coordinator",
        "scope_level": "STUDY_SITE",
        "permissions": (
            "SUBJECT.VIEW",
            "SUBJECT.CREATE",
            "SUBJECT.UPDATE",
            "CRF.VIEW",
            "CRF.ENTER",
            "CRF.UPDATE",
            "CRF.SUBMIT",
            "QUERY.VIEW",
            "QUERY.RESPOND",
            "VALIDATION_ISSUE.VIEW",
            "VALIDATION_ISSUE.ACKNOWLEDGE",
        ),
    },
    {
        "role_code": "CRA_MONITOR",
        "role_name": "CRA Monitor",
        "scope_level": "STUDY_SITE",
        "permissions": (
            "SUBJECT.VIEW",
            "CRF.VIEW",
            "QUERY.VIEW",
            "QUERY.CREATE",
            "QUERY.CLOSE",
            "QUERY.RETURN",
            "QUERY.CANCEL",
            "SDV.VIEW",
            "SDV.MARK",
            "SDR.MARK",
            "AUDIT_TRAIL.VIEW",
        ),
    },
    {
        "role_code": "DATA_MANAGER",
        "role_name": "Data Manager",
        "scope_level": "STUDY",
        "permissions": (
            "SUBJECT.VIEW",
            "CRF.VIEW",
            "QUERY.VIEW",
            "QUERY.CREATE",
            "QUERY.CLOSE",
            "QUERY.RETURN",
            "QUERY.CANCEL",
            "VALIDATION_ISSUE.VIEW",
            "USER_ACCESS.VIEW",
            "DATA.FREEZE",
            "DATA.LOCK",
            "DATA_EXPORT.RUN",
            "AUDIT_TRAIL.VIEW",
        ),
    },
    {
        "role_code": "STUDY_ADMIN",
        "role_name": "Study Admin",
        "scope_level": "STUDY",
        "permissions": (
            "STUDY_CONFIG.VIEW",
            "STUDY_CONFIG.MANAGE",
            "SUBJECT.VIEW",
            "CRF.VIEW",
            "CRF.UPDATE",
            "QUERY.VIEW",
            "QUERY.CREATE",
            "QUERY.RESPOND",
            "QUERY.CLOSE",
            "QUERY.RETURN",
            "QUERY.CANCEL",
            "SDV.VIEW",
            "SDV.MARK",
            "DATA.FREEZE",
            "DATA.UNFREEZE",
            "DATA.LOCK",
            "DATA.UNLOCK",
            "USER_ACCESS.VIEW",
            "USER_ACCESS.MANAGE",
            "AUDIT_TRAIL.VIEW",
            "DATA_EXPORT.RUN",
        ),
    },
)


def _to_legacy_role_group(role_definition):
    scope_level = str(role_definition["scope_level"]).upper()
    return {
        "group_name": role_definition["role_name"],
        "role_name": role_definition["role_name"],
        "role_code": role_definition["role_code"],
        "scope_level": scope_level,
        "scope": scope_level,
        "access_levels": (scope_level,),
        "permissions": tuple(role_definition["permissions"]),
    }


DEFAULT_EDC_ROLE_GROUPS = tuple(
    _to_legacy_role_group(role_definition)
    for role_definition in DEFAULT_EDC_ROLES
)

# Backward-compatible aliases for historical migrations.
DEFAULT_ROLE_GROUPS = DEFAULT_EDC_ROLE_GROUPS


__all__ = [
    "DEFAULT_EDC_PERMISSION_LABELS",
    "DEFAULT_EDC_ROLE_GROUPS",
    "DEFAULT_EDC_ROLES",
    "DEFAULT_PERMISSION_CONTENT_TYPES",
    "DEFAULT_PERMISSION_LABELS",
    "DEFAULT_ROLE_GROUPS",
]
