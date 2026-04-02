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
    }


class StudyAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_created(self, *, request, study):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_CREATED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            request=request,
            before_data={},
            after_data=_serialize_study_snapshot(study),
        )

    def record_updated(self, *, request, study, before_data):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_UPDATED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            request=request,
            before_data=before_data,
            after_data=_serialize_study_snapshot(study),
        )

    def record_status_changed(self, *, request, study):
        self.audit_context_adapter.record_event(
            action=AuditEventAction.STUDY_STATUS_CHANGED,
            object_type=AuditEventObjectType.STUDY,
            object_id=str(study.pk),
            request=request,
            before_data={"is_active": not study.is_active},
            after_data={"is_active": study.is_active},
        )
