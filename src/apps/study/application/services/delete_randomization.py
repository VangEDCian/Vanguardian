from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.application.commands.delete_randomization import (
    DeleteRandomizationArmCommand,
    DeleteRandomizationArmResult,
    DeleteRandomizationSchemeCommand,
    DeleteRandomizationSchemeResult,
    RandomizationArmNotFoundError,
    RandomizationDeleteBlockedError,
    RandomizationSchemeNotFoundError,
)
from apps.study.application.services.randomization_audit import (
    StudyRandomizationImportAuditService,
    serialize_randomization_arm_snapshot,
    serialize_randomization_scheme_snapshot,
)
from apps.study.infrastructure.repositories import DjangoRandomizationRepository


class DeleteRandomizationSchemeService:
    repository_class = DjangoRandomizationRepository
    randomization_audit_service_class = StudyRandomizationImportAuditService
    max_scheme_code_length = 64

    def __init__(self, randomization_audit_service=None, repository=None):
        self.repository = repository or self.repository_class()
        self.randomization_audit_service = (
            randomization_audit_service or self.randomization_audit_service_class()
        )

    @transaction.atomic
    def execute(self, command: DeleteRandomizationSchemeCommand) -> DeleteRandomizationSchemeResult:
        scheme = self.repository.get_scheme(
            study_id=command.study_id,
            scheme_id=command.scheme_id,
        )
        if scheme is None:
            raise RandomizationSchemeNotFoundError(command.scheme_id)

        if self.repository.scheme_has_assigned_slots(scheme_id=scheme.pk):
            raise RandomizationDeleteBlockedError(
                _("Cannot delete this randomization scheme because it has assigned slots."),
            )

        before_data = serialize_randomization_scheme_snapshot(scheme)
        now = self.repository.now()

        deleted_slot_count = self.repository.soft_delete_slots_for_scheme(
            scheme_id=scheme.pk,
            updated_at=now,
        )
        deleted_arm_count = self.repository.soft_delete_arms_for_scheme(
            scheme_id=scheme.pk,
            updated_at=now,
        )

        scheme.code = build_soft_deleted_unique_value(scheme.code)[: self.max_scheme_code_length]
        scheme.deleted = True
        scheme.updated_at = now
        self.repository.save_scheme(scheme, update_fields=["code", "deleted", "updated_at"])

        self.randomization_audit_service.record_scheme_deleted(
            scheme=scheme,
            actor_user_id=command.actor_user_id,
            before_data=before_data,
            deleted_slot_count=deleted_slot_count,
            deleted_arm_count=deleted_arm_count,
        )

        return DeleteRandomizationSchemeResult(
            deleted_slot_count=deleted_slot_count,
            deleted_arm_count=deleted_arm_count,
        )


class DeleteRandomizationArmService:
    repository_class = DjangoRandomizationRepository
    randomization_audit_service_class = StudyRandomizationImportAuditService
    max_arm_code_length = 32

    def __init__(self, randomization_audit_service=None, repository=None):
        self.repository = repository or self.repository_class()
        self.randomization_audit_service = (
            randomization_audit_service or self.randomization_audit_service_class()
        )

    @transaction.atomic
    def execute(self, command: DeleteRandomizationArmCommand) -> DeleteRandomizationArmResult:
        arm = self.repository.get_arm(study_id=command.study_id, arm_id=command.arm_id)
        if arm is None:
            raise RandomizationArmNotFoundError(command.arm_id)

        if self.repository.arm_has_assigned_slots(arm_id=arm.pk):
            raise RandomizationDeleteBlockedError(
                _("Cannot delete this randomization arm because it has assigned slots."),
            )

        before_data = serialize_randomization_arm_snapshot(arm)
        now = self.repository.now()

        deleted_slot_count = self.repository.soft_delete_slots_for_arm(
            arm_id=arm.pk,
            updated_at=now,
        )

        arm.arm_code = build_soft_deleted_unique_value(arm.arm_code)[: self.max_arm_code_length]
        arm.deleted = True
        arm.is_active = False
        arm.updated_at = now
        self.repository.save_arm(arm, update_fields=["arm_code", "deleted", "is_active", "updated_at"])

        self.randomization_audit_service.record_arm_deleted(
            arm=arm,
            actor_user_id=command.actor_user_id,
            before_data=before_data,
            deleted_slot_count=deleted_slot_count,
        )

        return DeleteRandomizationArmResult(deleted_slot_count=deleted_slot_count)


__all__ = [
    "DeleteRandomizationArmService",
    "DeleteRandomizationSchemeService",
]
