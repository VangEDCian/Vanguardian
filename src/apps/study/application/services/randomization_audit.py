from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventActionEnum, AuditEventObjectTypeEnum

__all__ = [
    "StudyRandomizationImportAuditService",
    "serialize_randomization_arm_snapshot",
    "serialize_randomization_scheme_snapshot",
    "serialize_randomization_sequence_period_snapshot",
]


def _serialize_datetime(value):
    return value.isoformat() if value else None


def serialize_randomization_scheme_snapshot(scheme):
    return {
        "study_id": scheme.study_id,
        "code": scheme.code,
        "name": scheme.name,
        "randomization_type": scheme.randomization_type,
        "allocation_ratio_json": scheme.allocation_ratio_json,
        "target_randomized_total": scheme.target_randomized_total,
        "eligibility_rule_code": scheme.eligibility_rule_code,
        "requires_screening_pass": scheme.requires_screening_pass,
        "is_open_label": scheme.is_open_label,
        "status": scheme.status,
        "effective_from": _serialize_datetime(scheme.effective_from),
        "effective_to": _serialize_datetime(scheme.effective_to),
        "deleted": scheme.deleted,
        "notes": scheme.notes,
    }


def serialize_randomization_arm_snapshot(arm):
    scheme_id = getattr(arm, "scheme_id", None)
    if scheme_id is None:
        scheme = getattr(arm, "scheme", None)
        scheme_id = getattr(scheme, "pk", None)
    return {
        "scheme_id": scheme_id,
        "arm_code": getattr(arm, "arm_code", None),
        "arm_name": getattr(arm, "arm_name", None),
        "target_count": getattr(arm, "target_count", None),
        "current_count": getattr(arm, "current_count", None),
        "display_order": getattr(arm, "display_order", None),
        "is_active": getattr(arm, "is_active", None),
        "deleted": getattr(arm, "deleted", None),
        "notes": getattr(arm, "notes", None),
    }


def serialize_randomization_sequence_period_snapshot(sequence_period):
    scheme_id = getattr(sequence_period, "scheme_id", None)
    if scheme_id is None:
        scheme = getattr(sequence_period, "scheme", None)
        scheme_id = getattr(scheme, "pk", None)
    arm_id = getattr(sequence_period, "arm_id", None)
    if arm_id is None:
        arm = getattr(sequence_period, "arm", None)
        arm_id = getattr(arm, "pk", None)
    start_event_definition_id = getattr(sequence_period, "start_event_definition_id", None)
    if start_event_definition_id is None:
        event_definition = getattr(sequence_period, "start_event_definition", None)
        start_event_definition_id = getattr(event_definition, "pk", None)
    end_event_definition_id = getattr(sequence_period, "end_event_definition_id", None)
    if end_event_definition_id is None:
        event_definition = getattr(sequence_period, "end_event_definition", None)
        end_event_definition_id = getattr(event_definition, "pk", None)
    return {
        "scheme_id": scheme_id,
        "arm_id": arm_id,
        "period_no": getattr(sequence_period, "period_no", None),
        "treatment_code": getattr(sequence_period, "treatment_code", None),
        "start_event_definition_id": start_event_definition_id,
        "end_event_definition_id": end_event_definition_id,
        "washout_days": getattr(sequence_period, "washout_days", None),
        "transition_rule_code": getattr(sequence_period, "transition_rule_code", None),
        "display_order": getattr(sequence_period, "display_order", None),
        "deleted": getattr(sequence_period, "deleted", None),
    }


class StudyRandomizationImportAuditService:
    audit_context_adapter_class = AuditContextAdapter

    def __init__(self, audit_context_adapter=None):
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()

    def record_scheme_inserted_by_import(self, *, scheme, actor_user_id):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_SCHEME_INSERTED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_SCHEME,
            object_id=str(scheme.pk),
            actor_user_id=actor_user_id,
            before_data={},
            after_data=serialize_randomization_scheme_snapshot(scheme),
        )

    def record_scheme_updated_by_import(self, *, scheme, actor_user_id, before_data):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_SCHEME_UPDATED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_SCHEME,
            object_id=str(scheme.pk),
            actor_user_id=actor_user_id,
            before_data=before_data,
            after_data=serialize_randomization_scheme_snapshot(scheme),
        )

    def record_arm_inserted_by_import(self, *, arm, actor_user_id):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_ARM_INSERTED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_ARM,
            object_id=str(arm.pk),
            actor_user_id=actor_user_id,
            before_data={},
            after_data=serialize_randomization_arm_snapshot(arm),
        )

    def record_arm_updated_by_import(self, *, arm, actor_user_id, before_data):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_ARM_UPDATED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_ARM,
            object_id=str(arm.pk),
            actor_user_id=actor_user_id,
            before_data=before_data,
            after_data=serialize_randomization_arm_snapshot(arm),
        )

    def record_sequence_period_inserted_by_import(self, *, sequence_period, actor_user_id):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_SEQUENCE_PERIOD_INSERTED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_SEQUENCE_PERIOD,
            object_id=str(sequence_period.pk),
            actor_user_id=actor_user_id,
            before_data={},
            after_data=serialize_randomization_sequence_period_snapshot(sequence_period),
        )

    def record_sequence_period_updated_by_import(self, *, sequence_period, actor_user_id, before_data):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_SEQUENCE_PERIOD_UPDATED_BY_IMPORT,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_SEQUENCE_PERIOD,
            object_id=str(sequence_period.pk),
            actor_user_id=actor_user_id,
            before_data=before_data,
            after_data=serialize_randomization_sequence_period_snapshot(sequence_period),
        )

    def record_scheme_deleted(self, *, scheme, actor_user_id, before_data, deleted_slot_count, deleted_arm_count):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_SCHEME_DELETED,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_SCHEME,
            object_id=str(scheme.pk),
            actor_user_id=actor_user_id,
            before_data=before_data,
            after_data={
                **serialize_randomization_scheme_snapshot(scheme),
                "deleted_slot_count": deleted_slot_count,
                "deleted_arm_count": deleted_arm_count,
            },
        )

    def record_arm_deleted(self, *, arm, actor_user_id, before_data, deleted_slot_count):
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_RANDOMIZATION_ARM_DELETED,
            object_type=AuditEventObjectTypeEnum.STUDY_RANDOMIZATION_ARM,
            object_id=str(arm.pk),
            actor_user_id=actor_user_id,
            before_data=before_data,
            after_data={
                **serialize_randomization_arm_snapshot(arm),
                "deleted_slot_count": deleted_slot_count,
            },
        )
