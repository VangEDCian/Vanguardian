from django.utils import timezone

from apps.core.choices.study import RandomizationSchemeStatusChoice, RandomizationSlotStatusChoice
from apps.study.infrastructure.persistence.models import (
    RandomizationArm,
    RandomizationScheme,
    RandomizationSlot,
)


class DjangoRandomizationRepository:
    def now(self):
        return timezone.now()

    def get_scheme(self, *, study_id, scheme_id):
        return RandomizationScheme.objects.filter(
            pk=scheme_id,
            study_id=study_id,
            deleted=False,
        ).first()

    def get_scheme_by_code(self, *, study_id, code):
        return RandomizationScheme.objects.filter(
            study_id=study_id,
            code__iexact=code,
        ).first()

    def list_schemes(self, *, study_id, include_deleted=True):
        queryset = RandomizationScheme.objects.filter(study_id=study_id)
        if not include_deleted:
            queryset = queryset.filter(deleted=False)
        return queryset

    def list_scheme_code_map(self, *, study_id):
        return {
            str(scheme.code).strip().lower(): scheme
            for scheme in self.list_schemes(study_id=study_id)
        }

    def list_active_scheme_map(self, *, study_id):
        return {
            str(scheme.code).strip().lower(): scheme
            for scheme in self.list_schemes(study_id=study_id, include_deleted=False)
        }

    def build_scheme(self, **values):
        return RandomizationScheme(**values)

    def create_scheme(self, **values):
        return RandomizationScheme.objects.create(**values)

    def save_scheme(self, scheme, *, update_fields):
        scheme.save(update_fields=update_fields)
        return scheme

    def scheme_has_assigned_slots(self, *, scheme_id):
        return RandomizationSlot.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
            status=RandomizationSlotStatusChoice.ASSIGNED,
        ).exists()

    def soft_delete_slots_for_scheme(self, *, scheme_id, updated_at):
        return RandomizationSlot.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=updated_at,
        )

    def soft_delete_arms_for_scheme(self, *, scheme_id, updated_at):
        return RandomizationArm.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=updated_at,
            is_active=False,
        )

    def get_arm(self, *, study_id, arm_id):
        return (
            RandomizationArm.objects.select_related("scheme")
            .filter(
                pk=arm_id,
                scheme__study_id=study_id,
                scheme__deleted=False,
                deleted=False,
            )
            .first()
        )

    def get_arm_by_code(self, *, scheme_id, arm_code):
        return RandomizationArm.objects.filter(
            scheme_id=scheme_id,
            arm_code__iexact=arm_code,
        ).first()

    def list_active_arms_for_scheme(self, *, scheme_id):
        return RandomizationArm.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
            is_active=True,
        )

    def list_arms_for_study(self, *, study_id):
        return RandomizationArm.objects.select_related("scheme").filter(
            scheme__study_id=study_id,
            scheme__deleted=False,
            deleted=False,
        )

    def list_arm_map(self, *, study_id):
        return {
            (str(arm.scheme.code).strip().lower(), str(arm.arm_code).strip().lower()): arm
            for arm in self.list_arms_for_study(study_id=study_id)
        }

    def build_arm(self, **values):
        return RandomizationArm(**values)

    def create_arm(self, **values):
        return RandomizationArm.objects.create(**values)

    def save_arm(self, arm, *, update_fields):
        arm.save(update_fields=update_fields)
        return arm

    def arm_has_assigned_slots(self, *, arm_id):
        return RandomizationSlot.objects.filter(
            arm_id=arm_id,
            deleted=False,
            status=RandomizationSlotStatusChoice.ASSIGNED,
        ).exists()

    def soft_delete_slots_for_arm(self, *, arm_id, updated_at):
        return RandomizationSlot.objects.filter(
            arm_id=arm_id,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=updated_at,
        )

    def count_assigned_slots_for_scheme(self, *, scheme_id):
        return RandomizationSlot.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
            status=RandomizationSlotStatusChoice.ASSIGNED,
        ).count()

    def list_slots_for_scheme(self, *, scheme_id):
        return RandomizationSlot.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
        ).order_by("sequence_no", "id")

    def void_available_slots(self, *, slot_ids, updated_at):
        if not slot_ids:
            return 0
        return RandomizationSlot.objects.filter(
            pk__in=slot_ids,
            deleted=False,
            status=RandomizationSlotStatusChoice.AVAILABLE,
        ).update(
            status=RandomizationSlotStatusChoice.VOID,
            void_reason="allocated slot",
            updated_at=updated_at,
        )

    def build_slot(self, **values):
        return RandomizationSlot(**values)

    def bulk_create_slots(self, slots):
        if not slots:
            return []
        return RandomizationSlot.objects.bulk_create(slots)

    def assign_random_available_slot_for_subject(
        self,
        *,
        study_id,
        subject_id,
        event_instance_id,
        actor_user_id,
        now,
        excluded_slot_ids=(),
    ):
        queryset = (
            RandomizationSlot.objects.select_for_update(nowait=True)
            .select_related("scheme", "arm")
            .filter(
                scheme__study_id=study_id,
                scheme__deleted=False,
                scheme__status=RandomizationSchemeStatusChoice.ACTIVE,
                deleted=False,
                status=RandomizationSlotStatusChoice.AVAILABLE,
            )
        )
        if excluded_slot_ids:
            queryset = queryset.exclude(pk__in=excluded_slot_ids)
        slot = queryset.order_by("?").first()
        if slot is None:
            return None

        updated = RandomizationSlot.objects.filter(
            pk=slot.pk,
            deleted=False,
            status=RandomizationSlotStatusChoice.AVAILABLE,
        ).update(
            status=RandomizationSlotStatusChoice.ASSIGNED,
            assigned_subject_id=subject_id,
            assigned_event_id=event_instance_id,
            assigned_at=now,
            updated_at=now,
        )
        return {
            "assigned": updated == 1,
            "slot_id": slot.pk,
            "scheme_id": slot.scheme_id,
            "scheme_code": slot.scheme.code,
            "arm_id": slot.arm_id,
            "arm_code": slot.arm.arm_code,
            "arm_name": slot.arm.arm_name,
            "sequence_no": slot.sequence_no,
        }
