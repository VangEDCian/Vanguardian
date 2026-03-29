import json
from dataclasses import dataclass

from apps.audit.infrastructure.persistence.repositories import DjangoAuditEventRepository


@dataclass(frozen=True)
class RecordAuditEventCommand:
    action: str
    object_type: str
    object_id: str
    before_data: object = None
    after_data: object = None
    user_id: int | None = None
    actor_user_id: int | None = None
    ip_address: str | None = None
    user_agent: str = ""


class RecordAuditEventService:
    repository_class = DjangoAuditEventRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: RecordAuditEventCommand):
        return self.repository.create(
            action=command.action.strip(),
            object_type=command.object_type.strip(),
            object_id=str(command.object_id).strip(),
            before_data=self._serialize_payload(command.before_data),
            after_data=self._serialize_payload(command.after_data),
            ip_address=(command.ip_address or "")[:39] or None,
            user_agent=(command.user_agent or "")[:255],
            user_id=command.user_id,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )

    @staticmethod
    def _serialize_payload(payload):
        if payload in (None, ""):
            return "{}"
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=True, default=str, sort_keys=True)
