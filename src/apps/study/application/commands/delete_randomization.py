from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.choices.study import RandomizationSlotStatusChoice
from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.application.services.randomization_audit import (
    StudyRandomizationImportAuditService,
    serialize_randomization_arm_snapshot,
    serialize_randomization_scheme_snapshot,
)
from apps.study.infrastructure.persistence.models import (
    RandomizationArm,
    RandomizationScheme,
    RandomizationSlot,
)


class RandomizationDeleteBlockedError(Exception):
    pass


class RandomizationSchemeNotFoundError(Exception):
    pass


class RandomizationArmNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class DeleteRandomizationSchemeCommand:
    actor_user_id: int
    study_id: int
    scheme_id: int


@dataclass(frozen=True)
class DeleteRandomizationArmCommand:
    actor_user_id: int
    study_id: int
    arm_id: int


@dataclass(frozen=True)
class DeleteRandomizationSchemeResult:
    deleted_slot_count: int
    deleted_arm_count: int


@dataclass(frozen=True)
class DeleteRandomizationArmResult:
    deleted_slot_count: int


class DeleteRandomizationSchemeService:
    randomization_scheme_model = RandomizationScheme
    randomization_arm_model = RandomizationArm
    randomization_slot_model = RandomizationSlot
    randomization_audit_service_class = StudyRandomizationImportAuditService
    max_scheme_code_length = 64

    def __init__(self, randomization_audit_service=None):
        self.randomization_audit_service = (
                randomization_audit_service or self.randomization_audit_service_class()
        )

    @transaction.atomic
    def execute(self, command: DeleteRandomizationSchemeCommand) -> DeleteRandomizationSchemeResult:
        scheme = self.randomization_scheme_model.objects.filter(
            pk=command.scheme_id,
            study_id=command.study_id,
            deleted=False,
        ).first()
        if scheme is None:
            raise RandomizationSchemeNotFoundError(command.scheme_id)

        if self.randomization_slot_model.objects.filter(
                scheme_id=scheme.pk,
                deleted=False,
                status=RandomizationSlotStatusChoice.ASSIGNED,
        ).exists():
            raise RandomizationDeleteBlockedError(
                _("Cannot delete this randomization scheme because it has assigned slots."),
            )

        before_data = serialize_randomization_scheme_snapshot(scheme)
        now = timezone.now()

        deleted_slot_count = self.randomization_slot_model.objects.filter(
            scheme_id=scheme.pk,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
        )
        deleted_arm_count = self.randomization_arm_model.objects.filter(
            scheme_id=scheme.pk,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
            is_active=False,
        )

        scheme.code = build_soft_deleted_unique_value(scheme.code)[: self.max_scheme_code_length]
        scheme.deleted = True
        scheme.updated_at = now
        scheme.save(update_fields=["code", "deleted", "updated_at"])

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
    randomization_arm_model = RandomizationArm
    randomization_slot_model = RandomizationSlot
    randomization_audit_service_class = StudyRandomizationImportAuditService
    max_arm_code_length = 32

    def __init__(self, randomization_audit_service=None):
        self.randomization_audit_service = (
                randomization_audit_service or self.randomization_audit_service_class()
        )

    @transaction.atomic
    def execute(self, command: DeleteRandomizationArmCommand) -> DeleteRandomizationArmResult:
        arm = self.randomization_arm_model.objects.select_related("scheme").filter(
            pk=command.arm_id,
            scheme__study_id=command.study_id,
            scheme__deleted=False,
            deleted=False,
        ).first()
        if arm is None:
            raise RandomizationArmNotFoundError(command.arm_id)

        if self.randomization_slot_model.objects.filter(
                arm_id=arm.pk,
                deleted=False,
                status=RandomizationSlotStatusChoice.ASSIGNED,
        ).exists():
            raise RandomizationDeleteBlockedError(
                _("Cannot delete this randomization arm because it has assigned slots."),
            )

        before_data = serialize_randomization_arm_snapshot(arm)
        now = timezone.now()

        deleted_slot_count = self.randomization_slot_model.objects.filter(
            arm_id=arm.pk,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
        )

        arm.arm_code = build_soft_deleted_unique_value(arm.arm_code)[: self.max_arm_code_length]
        arm.deleted = True
        arm.is_active = False
        arm.updated_at = now
        arm.save(update_fields=["arm_code", "deleted", "is_active", "updated_at"])

        self.randomization_audit_service.record_arm_deleted(
            arm=arm,
            actor_user_id=command.actor_user_id,
            before_data=before_data,
            deleted_slot_count=deleted_slot_count,
        )

        return DeleteRandomizationArmResult(deleted_slot_count=deleted_slot_count)
