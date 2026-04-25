from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventActionEnum, AuditEventObjectTypeEnum

__all__ = [
    "StudyRandomizationImportAuditService",
    "serialize_randomization_arm_snapshot",
    "serialize_randomization_scheme_snapshot",
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
    return {
        "scheme_id": arm.scheme_id,
        "arm_code": arm.arm_code,
        "arm_name": arm.arm_name,
        "target_count": arm.target_count,
        "current_count": arm.current_count,
        "display_order": arm.display_order,
        "is_active": arm.is_active,
        "deleted": arm.deleted,
        "notes": arm.notes,
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


