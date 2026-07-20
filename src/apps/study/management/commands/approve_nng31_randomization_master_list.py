from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.public import AuditContextAdapter
from apps.study.management.randomization_master_list import validate_stored_nng31_slots
from apps.study.models import (
    RandomizationArm,
    RandomizationScheme,
    RandomizationSequencePeriod,
    RandomizationSlot,
    Study,
)


class Command(BaseCommand):
    help = "Revalidate, approve, and permanently lock an imported NNG31 randomization master list."

    def add_arguments(self, parser):
        parser.add_argument("--study-id", required=True, type=int)
        parser.add_argument("--approver-id", required=True, type=int)
        parser.add_argument("--expected-checksum", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        study = Study.objects.filter(pk=options["study_id"], deleted=False).first()
        if study is None:
            raise CommandError("Study was not found.")
        scheme = RandomizationScheme.objects.filter(
            study=study,
            code="NNG31_XOVER",
            deleted=False,
        ).first()
        if scheme is None or not scheme.master_list_checksum:
            raise CommandError("Import the NNG31 master list before approval.")
        if scheme.master_list_locked_at is not None:
            raise CommandError("The NNG31 master list is already approved and locked.")
        if scheme.master_list_checksum.lower() != str(options["expected_checksum"]).strip().lower():
            raise CommandError("Expected checksum does not match the imported master list.")
        if scheme.master_list_imported_by_id == options["approver_id"]:
            raise CommandError("Importer and approver must be different users.")

        arms_by_code = {
            arm.arm_code: arm
            for arm in RandomizationArm.objects.filter(scheme=scheme, deleted=False, is_active=True)
        }
        slots = list(
            RandomizationSlot.objects.select_related("arm")
            .filter(scheme=scheme, deleted=False)
            .order_by("sequence_no")
        )
        validate_stored_nng31_slots(
            study=study,
            scheme=scheme,
            arms_by_code=arms_by_code,
            slots=slots,
        )
        self._validate_sequence_periods(scheme=scheme)
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Master list is valid and ready for approval. No DB changes."))
            return

        now = timezone.now()
        with transaction.atomic():
            scheme.master_list_approved_by_id = options["approver_id"]
            scheme.master_list_approved_at = now
            scheme.master_list_locked_at = now
            scheme.approved_by_id = options["approver_id"]
            scheme.updated_at = now
            scheme.save(
                update_fields=[
                    "master_list_approved_by_id",
                    "master_list_approved_at",
                    "master_list_locked_at",
                    "approved_by_id",
                    "updated_at",
                ]
            )
            AuditContextAdapter().record_event(
                action="randomization_master_list_approved",
                object_type="randomization_scheme",
                object_id=scheme.pk,
                actor_user_id=options["approver_id"],
                after_data={
                    "version": scheme.master_list_version,
                    "checksum_sha256": scheme.master_list_checksum,
                    "locked_at": now,
                },
            )
        self.stdout.write(self.style.SUCCESS("NNG31 master list approved and locked."))

    @staticmethod
    def _validate_sequence_periods(*, scheme):
        expected_treatments = {
            "SEQ_E_N": ("EPREX_4000U", "NANOKINE"),
            "SEQ_N_E": ("NANOKINE", "EPREX_4000U"),
        }
        periods = RandomizationSequencePeriod.objects.select_related("arm").filter(
            scheme=scheme,
            deleted=False,
            arm__deleted=False,
            arm__is_active=True,
        )
        actual = {}
        for period in periods.order_by("arm__arm_code", "period_no"):
            if period.start_event_definition_id is None or period.end_event_definition_id is None:
                raise CommandError("Every NNG31 sequence period must have both start and end events.")
            actual.setdefault(period.arm.arm_code, []).append((period.period_no, period.treatment_code))
        normalized = {
            arm_code: tuple(treatment_code for _period_no, treatment_code in values)
            for arm_code, values in actual.items()
            if tuple(period_no for period_no, _treatment_code in values) == (1, 2)
        }
        if normalized != expected_treatments:
            raise CommandError("NNG31 sequence periods must match the approved two-period crossover treatments.")
