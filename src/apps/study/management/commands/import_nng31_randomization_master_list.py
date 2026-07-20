from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.public import AuditContextAdapter
from apps.core.choices.study import RandomizationSlotStatusChoice
from apps.study.management.randomization_master_list import parse_and_validate_nng31_master_list
from apps.study.models import RandomizationArm, RandomizationScheme, RandomizationSlot, Study


class Command(BaseCommand):
    help = "Validate and import the NNG31 statistician-approved randomization master-list CSV."

    def add_arguments(self, parser):
        parser.add_argument("--study-id", required=True, type=int)
        parser.add_argument("--file", required=True)
        parser.add_argument("--master-list-version", required=True)
        parser.add_argument("--actor-id", required=True, type=int)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        source_path = Path(options["file"]).expanduser().resolve()
        try:
            content = source_path.read_bytes()
        except OSError as exc:
            raise CommandError(f"Cannot read master-list CSV: {exc}") from exc

        study = Study.objects.filter(pk=options["study_id"], deleted=False).first()
        if study is None:
            raise CommandError("Study was not found.")
        scheme = RandomizationScheme.objects.filter(
            study=study,
            code="NNG31_XOVER",
            deleted=False,
        ).first()
        if scheme is None:
            raise CommandError("Run seed_nng31_crossover_randomization before importing the master list.")
        if scheme.master_list_locked_at is not None:
            raise CommandError("The randomization master list is approved and locked; it cannot be replaced.")

        arms_by_code = {
            arm.arm_code: arm
            for arm in RandomizationArm.objects.filter(scheme=scheme, deleted=False, is_active=True)
        }
        rows, checksum = parse_and_validate_nng31_master_list(
            content=content,
            study=study,
            scheme=scheme,
            arms_by_code=arms_by_code,
        )
        master_list_version = str(options["master_list_version"] or "").strip()
        if not master_list_version:
            raise CommandError("Master-list version must not be blank.")
        existing_slots = list(RandomizationSlot.objects.filter(scheme=scheme, deleted=False))
        if len(existing_slots) not in (0, 44):
            raise CommandError("Existing scheme slots must be empty or contain exactly 44 rows.")
        existing_by_sequence = {slot.sequence_no: slot for slot in existing_slots}
        for row in rows:
            existing = existing_by_sequence.get(row.sequence_no)
            if (
                existing is not None
                and existing.status == RandomizationSlotStatusChoice.ASSIGNED
                and existing.arm_id != arms_by_code[row.arm_code].pk
            ):
                raise CommandError(
                    f"Assigned slot {row.sequence_no} conflicts with the statistician master list; manual review is required."
                )
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Valid master list: 44 rows, SHA-256 {checksum}. No DB changes."))
            return

        now = timezone.now()
        with transaction.atomic():
            for row in rows:
                existing = existing_by_sequence.get(row.sequence_no)
                defaults = {
                    "created_at": getattr(existing, "created_at", now),
                    "updated_at": now,
                    "deleted": False,
                    "arm": arms_by_code[row.arm_code],
                    "randomization_code": row.randomization_code,
                    "block_no": row.block_no,
                    "stratum_code": None,
                    "void_reason": None,
                }
                if existing is None or existing.status != RandomizationSlotStatusChoice.ASSIGNED:
                    defaults.update(
                        {
                            "status": RandomizationSlotStatusChoice.AVAILABLE,
                            "assigned_subject_id": None,
                            "assigned_event_id": None,
                            "assigned_at": None,
                        }
                    )
                RandomizationSlot.objects.update_or_create(
                    scheme=scheme,
                    sequence_no=row.sequence_no,
                    defaults=defaults,
                )
            scheme.master_list_version = master_list_version
            scheme.master_list_checksum = checksum
            scheme.master_list_source_filename = source_path.name
            scheme.master_list_imported_by_id = options["actor_id"]
            scheme.master_list_imported_at = now
            scheme.master_list_approved_by_id = None
            scheme.master_list_approved_at = None
            scheme.master_list_locked_at = None
            scheme.updated_at = now
            scheme.save(
                update_fields=[
                    "master_list_version",
                    "master_list_checksum",
                    "master_list_source_filename",
                    "master_list_imported_by_id",
                    "master_list_imported_at",
                    "master_list_approved_by_id",
                    "master_list_approved_at",
                    "master_list_locked_at",
                    "updated_at",
                ]
            )
            AuditContextAdapter().record_event(
                action="randomization_master_list_imported",
                object_type="randomization_scheme",
                object_id=scheme.pk,
                actor_user_id=options["actor_id"],
                after_data={
                    "version": scheme.master_list_version,
                    "checksum_sha256": checksum,
                    "source_filename": source_path.name,
                    "slot_count": 44,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Imported 44 slots. SHA-256: {checksum}. Approval is still required."))
