from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventAction, AuditEventObjectType


def _serialize_study_snapshot(study):
    return {
        "code": study.code,
        "name": study.name,
        "sponsor": study.sponsor,
        "description": study.description,
        "start_date": study.start_date.isoformat() if study.start_date else None,
        "end_date": study.end_date.isoformat() if study.end_date else None,
        "is_active": study.is_active,
        "subject_identifier_mode": study.subject_identifier_mode,
        "screening_identifier_mode": study.screening_identifier_mode,
        "subject_code_pattern": study.subject_code_pattern,
        "screening_code_pattern": study.screening_code_pattern,
        "subject_code_uniqueness_scope": study.subject_code_uniqueness_scope,
        "lock_subject_code_after_assignment": (
            study.lock_subject_code_after_assignment
        ),
    }


class StudyAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    serialize_snapshot = staticmethod(_serialize_study_snapshot)

    def record_created(self, *, study, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_CREATED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={},
            after_data=_serialize_study_snapshot(study),
        )

    def record_updated(self, *, study, before_data, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_UPDATED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data=before_data,
            after_data=_serialize_study_snapshot(study),
        )

    def record_status_changed(self, *, study, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_STATUS_CHANGED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data={"is_active": not study.is_active},
            after_data={"is_active": study.is_active},
        )

    def record_deleted(self, *, study, before_data, actor_user_id=None, ip_address=None, user_agent=None):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_DELETED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            before_data=before_data,
            after_data={**before_data, "deleted": True, "is_active": False},
        )
