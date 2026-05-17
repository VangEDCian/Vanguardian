import hashlib

from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventAction, AuditEventObjectType


class IdentityLoginAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_login_succeeded(self, *, user, identifier, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_LOGIN_SUCCEEDED,
            object_type=AuditEventObjectType.IDENTITY_USER,
            object_id=str(user.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.pk,
            before_data={},
            after_data={
                "identifier": identifier,
                "result": "succeeded",
            },
        )

    def record_login_failed(self, *, identifier, form_errors, actor_user_id=None, ip_address=None, user_agent=None):
        if not identifier:
            return

        self.audit_context_adapter.record_event(
            action=AuditEventAction.IDENTITY_LOGIN_FAILED,
            object_type=AuditEventObjectType.IDENTITY_LOGIN_ATTEMPT,
            object_id=self._build_failed_attempt_object_id(identifier),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={},
            after_data={
                "identifier": identifier,
                "result": "failed",
                "errors": form_errors,
            },
        )

    @staticmethod
    def _build_failed_attempt_object_id(identifier):
        normalized_identifier = identifier.strip().lower()
        return hashlib.sha256(normalized_identifier.encode("utf-8")).hexdigest()
