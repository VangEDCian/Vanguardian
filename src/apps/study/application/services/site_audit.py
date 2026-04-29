__all__ = [
    'SiteAuditService',
]

from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventActionEnum, AuditEventObjectTypeEnum


class SiteAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def _record(
            self,
            action: AuditEventActionEnum,
            object_id: int | str,
            actor_user_id: int | None = None,
            ip_address: str | None = None,
            user_agent: str | None = None,
            object_type: AuditEventObjectTypeEnum = AuditEventObjectTypeEnum.STUDY_SITE,
            before_data: dict | str | None = None,
            after_data: dict | str | None = None,
    ):
        if not before_data:
            before_data = {}

        if not after_data:
            after_data = {}

        return self.audit_context_adapter.record_event(
            action=action,
            object_type=object_type,
            object_id=str(object_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data=before_data,
            after_data=after_data,
        )

    def record_created(self, *, object_id: int | str, after_data: dict | str, actor_user_id=None, ip_address=None, user_agent=None):
        return self._record(
            action=AuditEventActionEnum.STUDY_SITE_CREATED,
            object_id=object_id,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            after_data=after_data,
        )

    def record_updated(self, *, object_id: int | str, before_data: dict | str, after_data: dict | str, actor_user_id=None, ip_address=None, user_agent=None):
        return self._record(
            action=AuditEventActionEnum.STUDY_SITE_UPDATED,
            object_id=object_id,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data=before_data,
            after_data=after_data,
        )

    def record_deleted(self, *, object_id: int | str, before_data: dict | str, actor_user_id=None, ip_address=None, user_agent=None):
        return self._record(
            action=AuditEventActionEnum.STUDY_SITE_DELETED,
            object_id=object_id,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data=before_data,
            after_data={},
        )
