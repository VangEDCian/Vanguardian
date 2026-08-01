from django.db.models import F

from apps.study.models import (
    RandomizationArm,
    RandomizationEvent,
    RandomizationScheme,
    RandomizationSequencePeriod,
    RandomizationSlot,
    Study,
)


class DjangoNng31MasterListRepository:
    def get_study(self, *, study_id):
        return Study.objects.filter(pk=study_id, deleted=False).first()

    def get_scheme(
        self,
        *,
        study_id,
        scheme_id=None,
        scheme_code=None,
        for_update=False,
    ):
        queryset = RandomizationScheme.objects.filter(
            study_id=study_id,
            deleted=False,
        )
        if for_update:
            queryset = queryset.select_for_update()
        if scheme_id is not None:
            queryset = queryset.filter(pk=scheme_id)
        if scheme_code is not None:
            queryset = queryset.filter(code__iexact=scheme_code)
        return queryset.first()

    def list_active_arms(self, *, scheme_id):
        return RandomizationArm.objects.filter(
            scheme_id=scheme_id,
            deleted=False,
            is_active=True,
        ).order_by("display_order", "id")

    def list_sequence_periods(self, *, scheme_id):
        return (
            RandomizationSequencePeriod.objects.select_related("arm")
            .filter(
                scheme_id=scheme_id,
                deleted=False,
                arm__deleted=False,
                arm__is_active=True,
            )
            .order_by("arm__display_order", "arm_id", "period_no", "display_order", "id")
        )

    def list_slots(self, *, scheme_id, for_update=False):
        queryset = (
            RandomizationSlot.objects.select_related("arm", "scheme")
            .filter(scheme_id=scheme_id, deleted=False)
            .order_by("sequence_no", "id")
        )
        if for_update:
            queryset = queryset.select_for_update()
        return queryset

    def update_or_create_slot(self, *, scheme, sequence_no, defaults):
        return RandomizationSlot.objects.update_or_create(
            scheme=scheme,
            sequence_no=sequence_no,
            defaults=defaults,
        )

    def replace_existing_slots(self, *, scheme, slot_rows, retired_slots=(), now):
        """Apply a complete master list while preserving existing slot identities."""
        imported_slots = [slot for slot, _values in slot_rows]
        all_slots = [*imported_slots, *retired_slots]
        slot_ids = [slot.pk for slot in all_slots]
        queryset = RandomizationSlot.objects.filter(
            scheme=scheme,
            pk__in=slot_ids,
            deleted=False,
        )
        temporary_offset = (
            max((int(slot.sequence_no) for slot in all_slots), default=0)
            + len(all_slots)
            + 1
        )
        queryset.update(
            sequence_no=F("sequence_no") + temporary_offset,
            randomization_code=None,
            updated_at=now,
        )

        for slot in retired_slots:
            slot.sequence_no += temporary_offset
            slot.randomization_code = None
            slot.deleted = True
            slot.updated_at = now
        if retired_slots:
            RandomizationSlot.objects.bulk_update(
                retired_slots,
                ["sequence_no", "randomization_code", "deleted", "updated_at"],
            )

        assigned_metadata = []
        for slot, values in slot_rows:
            slot.sequence_no = values["sequence_no"]
            slot.arm = values["arm"]
            slot.randomization_code = values["randomization_code"]
            slot.block_no = values["block_no"]
            slot.stratum_code = None
            slot.void_reason = None
            slot.deleted = False
            slot.updated_at = now
            if slot.status == "assigned":
                assigned_metadata.append(
                    {
                        "slot_id": slot.pk,
                        "arm_id": slot.arm_id,
                        "arm_code": str(slot.arm.arm_code),
                        "randomization_number": slot.randomization_code,
                    }
                )
            else:
                slot.status = "available"
                slot.assigned_subject_id = None
                slot.assigned_event_id = None
                slot.assigned_at = None

        if imported_slots:
            RandomizationSlot.objects.bulk_update(
                imported_slots,
                [
                    "sequence_no",
                    "arm",
                    "randomization_code",
                    "block_no",
                    "stratum_code",
                    "void_reason",
                    "deleted",
                    "updated_at",
                    "status",
                    "assigned_subject_id",
                    "assigned_event_id",
                    "assigned_at",
                ],
            )
        for metadata in assigned_metadata:
            RandomizationEvent.objects.filter(slot_id=metadata["slot_id"]).update(
                arm_id=metadata["arm_id"],
                randomization_sequence=metadata["arm_code"],
                randomization_number=metadata["randomization_number"],
            )
        return tuple(assigned_metadata)

    @staticmethod
    def save_scheme(scheme, *, update_fields):
        scheme.save(update_fields=update_fields)
        return scheme


__all__ = ["DjangoNng31MasterListRepository"]
