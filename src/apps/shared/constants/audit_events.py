class AuditEventAction:
    IDENTITY_USER_CREATED = "identity.user.created"
    IDENTITY_LOGIN_SUCCEEDED = "identity.login.succeeded"
    IDENTITY_LOGIN_FAILED = "identity.login.failed"
    IDENTITY_USER_UPDATED = "identity.user.updated"

    STUDY_CREATED = "study.created"
    STUDY_UPDATED = "study.updated"
    STUDY_STATUS_CHANGED = "study.status_changed"


class AuditEventObjectType:
    IDENTITY_USER = "identity.user"
    IDENTITY_LOGIN_ATTEMPT = "identity.login_attempt"

    STUDY = "study"
