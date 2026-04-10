import enum


class AuditEventAction:
    IDENTITY_USER_CREATED = "identity.user.created"
    IDENTITY_LOGIN_SUCCEEDED = "identity.login.succeeded"
    IDENTITY_LOGIN_FAILED = "identity.login.failed"
    IDENTITY_USER_UPDATED = "identity.user.updated"
    IDENTITY_USER_DELETED = "identity.user.deleted"
    IDENTITY_USER_RESTORED = "identity.user.restored"

    STUDY_CREATED = "study.created"
    STUDY_UPDATED = "study.updated"
    STUDY_STATUS_CHANGED = "study.status_changed"
    STUDY_DELETED = "study.deleted"


class AuditEventObjectType:
    IDENTITY_USER = "identity.user"
    IDENTITY_LOGIN_ATTEMPT = "identity.login_attempt"

    STUDY = "study"


class AuditEventActionEnum(enum.Enum):
    STUDY_SITE_CREATED = "study.site.created"
    STUDY_SITE_UPDATED = "study.site.updated"
    STUDY_SITE_DELETED = "study.site.deleted"

    IDENTITY_USER_CHANGE_PASSWORD = "identity.user.change_password"
    IDENTITY_USER_ADMIN_SET_PASSWORD = "identity.user.admin_set_password"


class AuditEventObjectTypeEnum(enum.Enum):
    STUDY_SITE = "study.site"
    IDENTITY_USER = "identity.user"
