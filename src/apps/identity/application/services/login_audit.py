import hashlib

from apps.audit.public import AuditContextAdapter


class IdentityLoginAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_login_succeeded(self, *, request, user, identifier):
        self.audit_context_adapter.record_event(
            action="identity.login.succeeded",
            object_type="identity.user",
            object_id=str(user.pk),
            request=request,
            user_id=user.pk,
            actor_user_id=user.pk,
            before_data={},
            after_data={
                "identifier": identifier,
                "result": "succeeded",
            },
        )

    def record_login_failed(self, *, request, identifier, form_errors):
        if not identifier:
            return

        self.audit_context_adapter.record_event(
            action="identity.login.failed",
            object_type="identity.login_attempt",
            object_id=self._build_failed_attempt_object_id(identifier),
            request=request,
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
