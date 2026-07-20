import json
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.public import AuditContextAdapter
from apps.core.choices.study import (
    RandomizationSchemeStatusChoice,
    RandomizationSlotStatusChoice,
)
from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.models import (
    RandomizationArm,
    RandomizationEvent,
    RandomizationScheme,
    RandomizationSequencePeriod,
    RandomizationSlot,
    Study,
)
from apps.subject.models import Subject, SubjectPeriod, SubjectRandomization

DEFAULT_LEGACY_SCHEME_CODE = "CROSS_OVER_NANOKINE_EPREX4000IU"


@dataclass(frozen=True)
class LegacyAssignmentMigration:
    assignment: SubjectRandomization
    source_scheme: RandomizationScheme
    source_slot: RandomizationSlot
    target_slot: RandomizationSlot
    subject_code: str


class Command(BaseCommand):
    help = (
        "Migrate legacy NNG31 assignments to NNG31_XOVER, reconcile identifiers, "
        "and retire migrated legacy schemes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--study-id", required=True, type=int)
        parser.add_argument("--actor-id", required=True, type=int)
        parser.add_argument(
            "--legacy-scheme-code",
            action="append",
            dest="legacy_scheme_codes",
            help=(
                "Legacy scheme code to migrate. May be repeated. Defaults to "
                f"{DEFAULT_LEGACY_SCHEME_CODE}."
            ),
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        study = Study.objects.filter(
            pk=options["study_id"],
            code__iexact="NNG31",
            deleted=False,
        ).first()
        if study is None:
            raise CommandError("NNG31 study was not found.")

        target_scheme = RandomizationScheme.objects.filter(
            study=study,
            code="NNG31_XOVER",
            deleted=False,
        ).first()
        if target_scheme is None or not target_scheme.master_list_checksum:
            raise CommandError("Import and validate the NNG31 master list before reconciliation.")

        legacy_scheme_codes = options.get("legacy_scheme_codes") or [DEFAULT_LEGACY_SCHEME_CODE]
        legacy_schemes = list(
            RandomizationScheme.objects.filter(
                study=study,
                code__in=legacy_scheme_codes,
                deleted=False,
            ).order_by("id")
        )
        target_slots = list(
            RandomizationSlot.objects.select_related("arm")
            .filter(scheme=target_scheme, deleted=False)
            .order_by("sequence_no")
        )
        target_slots_by_sequence = {slot.sequence_no: slot for slot in target_slots}
        target_periods_by_arm = self._build_periods_by_arm(
            scheme_ids=[target_scheme.pk],
        )
        source_periods_by_arm = self._build_periods_by_arm(
            scheme_ids=[scheme.pk for scheme in legacy_schemes],
        )

        migrations = self._build_legacy_migrations(
            study=study,
            legacy_schemes=legacy_schemes,
            source_periods_by_arm=source_periods_by_arm,
            target_periods_by_arm=target_periods_by_arm,
            target_slots_by_sequence=target_slots_by_sequence,
        )
        target_assignments = list(
            SubjectRandomization.objects.select_related("subject", "slot", "arm")
            .filter(
                study=study,
                scheme=target_scheme,
                deleted=False,
                slot__isnull=False,
            )
            .order_by("slot__sequence_no")
        )
        reconciliations = [
            (
                assignment,
                self._validate_target_assignment(assignment=assignment),
            )
            for assignment in target_assignments
        ]

        if not options["apply"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dry run passed: "
                    f"{len(migrations)} legacy assignment(s) will be migrated, "
                    f"{len(reconciliations)} current assignment(s) will be reconciled, "
                    f"and {len(legacy_schemes)} legacy scheme(s) will be retired. "
                    "Use --apply to write."
                )
            )
            return

        now = timezone.now()
        with transaction.atomic():
            for migration in migrations:
                self._apply_legacy_migration(
                    migration=migration,
                    target_scheme=target_scheme,
                    target_periods_by_arm=target_periods_by_arm,
                    actor_user_id=options["actor_id"],
                    now=now,
                )
            for assignment, subject_code in reconciliations:
                self._reconcile_assignment(
                    assignment=assignment,
                    subject_code=subject_code,
                    target_periods_by_arm=target_periods_by_arm,
                    actor_user_id=options["actor_id"],
                    now=now,
                )
            retired_scheme_count = self._retire_legacy_schemes(
                legacy_schemes=legacy_schemes,
                actor_user_id=options["actor_id"],
                now=now,
            )
            self._refresh_arm_counts(target_scheme=target_scheme, now=now)
            AuditContextAdapter().record_event(
                action="randomization_identifiers_reconciled",
                object_type="randomization_scheme",
                object_id=target_scheme.pk,
                actor_user_id=options["actor_id"],
                after_data={
                    "checksum_sha256": target_scheme.master_list_checksum,
                    "legacy_assignment_count": len(migrations),
                    "reconciled_assignment_count": len(reconciliations),
                    "retired_legacy_scheme_count": retired_scheme_count,
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated {len(migrations)} legacy assignment(s), "
                f"reconciled {len(reconciliations)} current assignment(s), and "
                f"retired {retired_scheme_count} legacy scheme(s)."
            )
        )

    @staticmethod
    def _build_periods_by_arm(*, scheme_ids):
        periods_by_arm = {}
        periods = (
            RandomizationSequencePeriod.objects.filter(
                scheme_id__in=scheme_ids,
                deleted=False,
                arm__deleted=False,
            )
            .select_related("arm")
            .order_by("arm_id", "period_no")
        )
        for period in periods:
            periods_by_arm.setdefault(period.arm_id, []).append(period)
        return {
            arm_id: tuple(arm_periods)
            for arm_id, arm_periods in periods_by_arm.items()
        }

    def _build_legacy_migrations(
        self,
        *,
        study,
        legacy_schemes,
        source_periods_by_arm,
        target_periods_by_arm,
        target_slots_by_sequence,
    ):
        legacy_assignments = list(
            SubjectRandomization.objects.select_related("subject", "scheme", "slot", "arm")
            .filter(
                study=study,
                scheme__in=legacy_schemes,
                deleted=False,
                slot__isnull=False,
            )
            .order_by("randomization_datetime", "slot__sequence_no", "id")
        )
        migrations = []
        for assignment in legacy_assignments:
            source_slot = assignment.slot
            target_slot = target_slots_by_sequence.get(source_slot.sequence_no)
            if target_slot is None:
                raise CommandError(
                    f"Target slot R-{source_slot.sequence_no:03} was not found for legacy "
                    f"slot {source_slot.pk}."
                )
            subject_code = self._get_subject_code(assignment=assignment)
            self._validate_randomization_code(slot=target_slot)
            self._validate_target_slot_available(
                target_slot=target_slot,
                subject_id=assignment.subject_id,
            )
            source_signature = self._treatment_signature(
                periods=source_periods_by_arm.get(assignment.arm_id, ()),
            )
            target_signature = self._treatment_signature(
                periods=target_periods_by_arm.get(target_slot.arm_id, ()),
            )
            if not source_signature or source_signature != target_signature:
                raise CommandError(
                    f"Legacy assigned slot {source_slot.sequence_no} for subject {subject_code} "
                    f"has treatment sequence {source_signature or 'undefined'}, but target "
                    f"{target_slot.randomization_code} has {target_signature or 'undefined'}. "
                    "Re-import the authoritative master list preserving the existing "
                    "treatment before applying migration."
                )
            migrations.append(
                LegacyAssignmentMigration(
                    assignment=assignment,
                    source_scheme=assignment.scheme,
                    source_slot=source_slot,
                    target_slot=target_slot,
                    subject_code=subject_code,
                )
            )
        return migrations

    def _validate_target_assignment(self, *, assignment):
        self._validate_randomization_code(slot=assignment.slot)
        self._validate_target_slot_available(
            target_slot=assignment.slot,
            subject_id=assignment.subject_id,
            allow_same_assignment=True,
        )
        return self._get_subject_code(assignment=assignment)

    @staticmethod
    def _get_subject_code(*, assignment):
        subject_code = str(assignment.subject.subject_code or "").strip()
        if not subject_code:
            raise CommandError(
                f"Subject {assignment.subject_id} has no subject code; assign its NNG31 identifier first."
            )
        conflict = Subject.objects.filter(
            study=assignment.study,
            site_id=assignment.site_id,
            subject_code=subject_code,
            deleted=False,
        ).exclude(pk=assignment.subject_id).exists()
        if conflict:
            raise CommandError(
                f"Subject code {subject_code} is already used by another subject at the same site."
            )
        return subject_code

    @staticmethod
    def _validate_randomization_code(*, slot):
        expected_randomization_code = f"R-{slot.sequence_no:03}"
        randomization_code = str(slot.randomization_code or "").strip()
        if randomization_code != expected_randomization_code:
            raise CommandError(
                f"Target slot {slot.pk} must use Randomization ID {expected_randomization_code}."
            )

    @staticmethod
    def _validate_target_slot_available(*, target_slot, subject_id, allow_same_assignment=False):
        is_same_assignment = (
            allow_same_assignment
            and target_slot.status == RandomizationSlotStatusChoice.ASSIGNED
            and target_slot.assigned_subject_id == subject_id
        )
        if target_slot.status == RandomizationSlotStatusChoice.AVAILABLE or is_same_assignment:
            return
        raise CommandError(
            f"Target slot {target_slot.randomization_code} is already assigned to "
            f"subject {target_slot.assigned_subject_id}."
        )

    @staticmethod
    def _treatment_signature(*, periods):
        ordered_periods = sorted(periods, key=lambda period: period.period_no)
        if [period.period_no for period in ordered_periods] != [1, 2]:
            return ()
        return tuple(period.treatment_code for period in ordered_periods)

    def _apply_legacy_migration(
        self,
        *,
        migration,
        target_scheme,
        target_periods_by_arm,
        actor_user_id,
        now,
    ):
        assignment = migration.assignment
        target_slot = migration.target_slot
        before_data = {
            "scheme_id": assignment.scheme_id,
            "arm_id": assignment.arm_id,
            "slot_id": assignment.slot_id,
            "randomization_number": assignment.randomization_number,
            "randomization_sequence": assignment.randomization_sequence,
        }
        target_slot.status = RandomizationSlotStatusChoice.ASSIGNED
        target_slot.assigned_subject_id = assignment.subject_id
        target_slot.assigned_event_id = migration.source_slot.assigned_event_id
        target_slot.assigned_at = migration.source_slot.assigned_at or assignment.randomization_datetime
        target_slot.updated_at = now
        target_slot.save(
            update_fields=[
                "status",
                "assigned_subject_id",
                "assigned_event_id",
                "assigned_at",
                "updated_at",
            ]
        )

        assignment.scheme = target_scheme
        assignment.arm = target_slot.arm
        assignment.slot = target_slot
        assignment.randomization_number = target_slot.randomization_code
        assignment.randomization_sequence = target_slot.arm.arm_code
        assignment.updated_at = now
        assignment.updated_by_id = actor_user_id
        assignment.save(
            update_fields=[
                "scheme",
                "arm",
                "slot",
                "randomization_number",
                "randomization_sequence",
                "updated_at",
                "updated_by_id",
            ]
        )
        self._update_subject_periods(
            assignment=assignment,
            subject_code=migration.subject_code,
            target_periods_by_arm=target_periods_by_arm,
            actor_user_id=actor_user_id,
            now=now,
        )
        after_data = {
            "scheme_id": target_scheme.pk,
            "arm_id": target_slot.arm_id,
            "slot_id": target_slot.pk,
            "randomization_number": target_slot.randomization_code,
            "randomization_sequence": target_slot.arm.arm_code,
        }
        RandomizationEvent.objects.create(
            created_at=now,
            event_type="Migrated",
            randomization_status=assignment.randomization_status,
            randomization_datetime=assignment.randomization_datetime,
            randomization_sequence=target_slot.arm.arm_code,
            randomization_number=target_slot.randomization_code,
            randomization_source="migration",
            reason_code="legacy_scheme_reconcile",
            reason_text="Migrated from legacy NNG31 crossover randomization scheme.",
            before_data=json.dumps(before_data, ensure_ascii=True, sort_keys=True),
            after_data=json.dumps(after_data, ensure_ascii=True, sort_keys=True),
            subject_id=assignment.subject_id,
            study_id=assignment.study_id,
            scheme=target_scheme,
            arm=target_slot.arm,
            slot=target_slot,
            actor_id=actor_user_id,
            created_by_id=actor_user_id,
        )

    def _reconcile_assignment(
        self,
        *,
        assignment,
        subject_code,
        target_periods_by_arm,
        actor_user_id,
        now,
    ):
        assignment.randomization_number = assignment.slot.randomization_code
        assignment.randomization_sequence = assignment.arm.arm_code
        assignment.updated_at = now
        assignment.updated_by_id = actor_user_id
        assignment.save(
            update_fields=[
                "randomization_number",
                "randomization_sequence",
                "updated_at",
                "updated_by_id",
            ]
        )
        RandomizationEvent.objects.filter(
            subject_id=assignment.subject_id,
            scheme_id=assignment.scheme_id,
            slot_id=assignment.slot_id,
        ).update(
            randomization_number=assignment.slot.randomization_code,
            randomization_sequence=assignment.arm.arm_code,
        )
        self._update_subject_periods(
            assignment=assignment,
            subject_code=subject_code,
            target_periods_by_arm=target_periods_by_arm,
            actor_user_id=actor_user_id,
            now=now,
        )

    @staticmethod
    def _update_subject_periods(
        *,
        assignment,
        subject_code,
        target_periods_by_arm,
        actor_user_id,
        now,
    ):
        target_periods = {
            period.period_no: period
            for period in target_periods_by_arm.get(assignment.arm_id, ())
        }
        for period in SubjectPeriod.objects.filter(
            subject_id=assignment.subject_id,
            deleted=False,
        ):
            target_period = target_periods.get(period.period_no)
            if target_period is None:
                raise CommandError(
                    f"Target sequence period {period.period_no} was not found for "
                    f"subject {subject_code}."
                )
            kit_code = subject_code if period.period_no == 1 else f"R-{subject_code}"
            if period.period_no > 2:
                kit_code = f"P{period.period_no}-{subject_code}"
            period.sequence_period = target_period
            period.treatment_code = target_period.treatment_code
            period.kit_code = kit_code
            period.updated_at = now
            period.updated_by_id = actor_user_id
            period.save(
                update_fields=[
                    "sequence_period",
                    "treatment_code",
                    "kit_code",
                    "updated_at",
                    "updated_by_id",
                ]
            )

    @staticmethod
    def _retire_legacy_schemes(*, legacy_schemes, actor_user_id, now):
        retired_count = 0
        for scheme in legacy_schemes:
            if SubjectRandomization.objects.filter(
                scheme=scheme,
                deleted=False,
            ).exists():
                raise CommandError(
                    f"Legacy scheme {scheme.code} still has active subject assignments."
                )
            RandomizationSlot.objects.filter(scheme=scheme, deleted=False).update(
                deleted=True,
                updated_at=now,
            )
            RandomizationSequencePeriod.objects.filter(scheme=scheme, deleted=False).update(
                deleted=True,
                updated_at=now,
            )
            RandomizationArm.objects.filter(scheme=scheme, deleted=False).update(
                deleted=True,
                is_active=False,
                updated_at=now,
            )
            scheme.code = build_soft_deleted_unique_value(scheme.code)[:64]
            scheme.status = RandomizationSchemeStatusChoice.CLOSED
            scheme.deleted = True
            scheme.updated_at = now
            scheme.save(update_fields=["code", "status", "deleted", "updated_at"])
            retired_count += 1
        return retired_count

    @staticmethod
    def _refresh_arm_counts(*, target_scheme, now):
        for arm in RandomizationArm.objects.filter(
            scheme=target_scheme,
            deleted=False,
            is_active=True,
        ):
            arm.current_count = SubjectRandomization.objects.filter(
                scheme=target_scheme,
                arm=arm,
                randomization_status="assigned",
                deleted=False,
            ).count()
            arm.updated_at = now
            arm.save(update_fields=["current_count", "updated_at"])
