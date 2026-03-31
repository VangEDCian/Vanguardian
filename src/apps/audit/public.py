from apps.audit.application import RecordAuditEventCommand, RecordAuditEventService


class AuditContextAdapter:
    def __init__(self, record_audit_event_service=None):
        self.record_audit_event_service = record_audit_event_service or RecordAuditEventService()

    def record_event(
        self,
        *,
        action,
        object_type,
        object_id,
        request=None,
        before_data=None,
        after_data=None,
        user_id=None,
        actor_user_id=None,
    ):
        command = RecordAuditEventCommand(
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_data=before_data,
            after_data=after_data,
            user_id=user_id,
            actor_user_id=actor_user_id or self._resolve_actor_user_id(request),
            ip_address=self._resolve_ip_address(request),
            user_agent=self._resolve_user_agent(request),
        )
        return self.record_audit_event_service.execute(command)

    @staticmethod
    def _resolve_actor_user_id(request):
        request_user = getattr(request, "user", None)
        if request_user is None or not getattr(request_user, "is_authenticated", False):
            return None
        return request_user.pk

    @staticmethod
    def _resolve_ip_address(request):
        if request is None:
            return None

        forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()[:39] or None

        return ((request.META.get("REMOTE_ADDR") or "").strip()[:39]) or None

    @staticmethod
    def _resolve_user_agent(request):
        if request is None:
            return ""
        return (request.META.get("HTTP_USER_AGENT") or "").strip()[:255]
