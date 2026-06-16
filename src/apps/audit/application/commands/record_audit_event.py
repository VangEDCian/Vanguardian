from dataclasses import dataclass


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
