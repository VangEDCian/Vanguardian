class AuditEventAction:
    IDENTITY_LOGIN_SUCCEEDED = "identity.login.succeeded"
    IDENTITY_LOGIN_FAILED = "identity.login.failed"


class AuditEventObjectType:
    IDENTITY_USER = "identity.user"
    IDENTITY_LOGIN_ATTEMPT = "identity.login_attempt"
