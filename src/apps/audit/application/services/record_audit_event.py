import json

from apps.audit.application.commands.record_audit_event import RecordAuditEventCommand
from apps.audit.infrastructure.repositories import DjangoAuditEventRepository


class RecordAuditEventService:
    repository_class = DjangoAuditEventRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: RecordAuditEventCommand):
        actor_id = command.actor_user_id or command.user_id
        return self.repository.create(
            action=self._normalize_text(command.action),
            object_type=self._normalize_text(command.object_type),
            object_id=self._normalize_text(command.object_id),
            before_data=self._serialize_payload(command.before_data),
            after_data=self._serialize_payload(command.after_data),
            ip_address=(command.ip_address or "")[:39] or None,
            user_agent=(command.user_agent or "")[:255],
            user_id=actor_id,
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )

    @staticmethod
    def _serialize_payload(payload):
        if payload in (None, ""):
            return "{}"
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=True, default=str, sort_keys=True)

    @staticmethod
    def _normalize_text(value) -> str:
        if value is None:
            return ""
        enum_value = getattr(value, "value", None)
        if enum_value is not None:
            value = enum_value
        return str(value).strip()


__all__ = ["RecordAuditEventService"]
