import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit.public import AuditContextAdapter
from apps.core.choices.study import RandomizationSlotStatusChoice
from apps.study.application.commands import (
    ApproveNng31MasterListCommand,
    ApproveNng31MasterListResult,
    CommitNng31MasterListCommand,
    CommitNng31MasterListResult,
    PreviewRandomizationImportCommand,
)
from apps.study.application.exceptions import RandomizationImportValidationError
from apps.study.application.use_cases.randomization_import_preview import (
    Nng31RandomizationMasterListImportPreviewUseCase,
    RandomizationImportColumn,
    RandomizationImportIssue,
    RandomizationImportParsedRow,
    RandomizationImportPreviewResult,
    RandomizationImportPreviewRow,
)
from apps.study.domain import (
    RandomizationCodeConfigurationError,
    format_scheme_randomization_code,
)
from apps.study.infrastructure.repositories import DjangoNng31MasterListRepository

EXPECTED_BLOCK_SIZES = (4, 4, 4, 4, 4, 6, 6, 6, 6)
EXPECTED_RANDOMIZATION_TOTAL = sum(EXPECTED_BLOCK_SIZES)


@dataclass(frozen=True)
class Nng31MasterListPreviewResult(RandomizationImportPreviewResult):
    checksum: str = ""
    scheme_id: int | None = None


class PreviewNng31MasterListImportService:
    preview_use_case_class = Nng31RandomizationMasterListImportPreviewUseCase
    repository_class = DjangoNng31MasterListRepository

    def __init__(self, preview_use_case=None, repository=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()
        self.repository = repository or self.repository_class()

    def execute(
        self,
        command: PreviewRandomizationImportCommand,
    ) -> Nng31MasterListPreviewResult:
        preview_result = self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )
        checksum = hashlib.sha256(command.file_content).hexdigest()
        study = self.repository.get_study(study_id=command.study_id)
        scheme_codes = {
            str(row.values.get("scheme_code", "")).strip()
            for row in preview_result.parsed_rows
            if str(row.values.get("scheme_code", "")).strip()
        }
        scheme = None
        if study is not None and len(scheme_codes) == 1:
            scheme = self.repository.get_scheme(
                study_id=command.study_id,
                scheme_code=next(iter(scheme_codes)),
            )

        arms = list(self.repository.list_active_arms(scheme_id=scheme.pk)) if scheme else []
        periods = list(self.repository.list_sequence_periods(scheme_id=scheme.pk)) if scheme else []
        treatment_by_arm = self._build_treatment_by_arm(periods)
        issues = [
            *preview_result.issues,
            *self._build_configuration_issues(
                study=study,
                scheme=scheme,
                scheme_codes=scheme_codes,
                parsed_rows=preview_result.parsed_rows,
                arms=arms,
                periods=periods,
            ),
        ]
        columns, preview_rows = self._append_treatment_preview(
            preview_result=preview_result,
            treatment_by_arm=treatment_by_arm,
        )
        return Nng31MasterListPreviewResult(
            columns=columns,
            preview_rows=preview_rows,
            parsed_rows=preview_result.parsed_rows,
            total_rows=preview_result.total_rows,
            issues=tuple(issues),
            checksum=checksum,
            scheme_id=getattr(scheme, "pk", None),
        )

    @staticmethod
    def _build_treatment_by_arm(periods):
        treatments = defaultdict(list)
        for period in periods:
            treatments[str(period.arm.arm_code).strip()].append(
                (int(period.period_no), str(period.treatment_code or "").strip())
            )
        return {
            arm_code: tuple(treatment for _period_no, treatment in values)
            for arm_code, values in treatments.items()
        }

    @staticmethod
    def _append_treatment_preview(*, preview_result, treatment_by_arm):
        parsed_by_row = {row.row_number: row for row in preview_result.parsed_rows}
        preview_rows = []
        for preview_row in preview_result.preview_rows:
            parsed_row = parsed_by_row.get(preview_row.row_number)
            arm_code = (
                str(parsed_row.values.get("arm_code", "")).strip()
                if parsed_row is not None
                else ""
            )
            treatment_sequence = " → ".join(treatment_by_arm.get(arm_code, ()))
            preview_rows.append(
                RandomizationImportPreviewRow(
                    row_number=preview_row.row_number,
                    values=(*preview_row.values, treatment_sequence),
                )
            )
        return (
            (
                *preview_result.columns,
                RandomizationImportColumn(
                    "treatment_sequence",
                    "Treatment Sequence",
                    required=False,
                ),
            ),
            tuple(preview_rows),
        )

    def _build_configuration_issues(
        self,
        *,
        study,
        scheme,
        scheme_codes,
        parsed_rows,
        arms,
        periods,
    ):
        issues = []
        first_row = parsed_rows[0].row_number if parsed_rows else 1
        if study is None:
            return (self._issue(first_row, "Study", "Study was not found."),)
        if str(study.code or "").strip().upper() != "NNG31":
            issues.append(
                self._issue(
                    first_row,
                    "Study",
                    "This master-list workflow only accepts study NNG31.",
                )
            )
        if len(scheme_codes) != 1:
            issues.append(
                self._issue(
                    first_row,
                    "Scheme Code",
                    "Every row must reference one identical Scheme Code.",
                )
            )
            return tuple(issues)
        if scheme is None:
            issues.append(
                self._issue(
                    first_row,
                    "Scheme Code",
                    "The configured randomization scheme was not found in this study.",
                )
            )
            return tuple(issues)
        if scheme.master_list_locked_at is not None:
            issues.append(
                self._issue(
                    first_row,
                    "Scheme Code",
                    "The randomization master list is approved and locked; it cannot be replaced.",
                )
            )
        has_randomization_code_prefix = bool(
            str(scheme.randomization_code_prefix or "").strip()
        )
        if not has_randomization_code_prefix:
            issues.append(
                self._issue(
                    first_row,
                    "Randomization ID",
                    "Configure Randomization Code Prefix on the scheme before importing the master list.",
                )
            )
        if len(parsed_rows) != EXPECTED_RANDOMIZATION_TOTAL:
            issues.append(
                self._issue(
                    first_row,
                    "Randomization ID",
                    f"NNG31 master list must contain exactly {EXPECTED_RANDOMIZATION_TOTAL} allocations.",
                )
            )
        if int(scheme.target_randomized_total or 0) != EXPECTED_RANDOMIZATION_TOTAL:
            issues.append(
                self._issue(
                    first_row,
                    "Scheme Code",
                    f"Scheme target must be exactly {EXPECTED_RANDOMIZATION_TOTAL} allocations.",
                )
            )

        expected_sequences = list(range(1, EXPECTED_RANDOMIZATION_TOTAL + 1))
        actual_sequences = [int(row.values["sequence_no"]) for row in parsed_rows]
        if actual_sequences != expected_sequences:
            issues.append(
                self._issue(
                    first_row,
                    "Sequence No",
                    f"Sequence No must be ordered, unique, and contiguous from 1 through {EXPECTED_RANDOMIZATION_TOTAL}.",
                )
            )
        expected_codes = []
        if has_randomization_code_prefix:
            try:
                expected_codes = [
                    format_scheme_randomization_code(
                        scheme=scheme,
                        sequence_no=sequence_no,
                    )
                    for sequence_no in expected_sequences
                ]
            except RandomizationCodeConfigurationError as exc:
                issues.append(self._issue(first_row, "Randomization ID", str(exc)))
        actual_codes = [str(row.values["randomization_code"]).strip() for row in parsed_rows]
        if expected_codes and actual_codes != expected_codes:
            issues.append(
                self._issue(
                    first_row,
                    "Randomization ID",
                    f"Randomization ID must be ordered exactly from {expected_codes[0]} through {expected_codes[-1]}.",
                )
            )

        arm_by_code = {str(arm.arm_code).strip(): arm for arm in arms}
        used_arm_codes = [str(row.values["arm_code"]).strip() for row in parsed_rows]
        unknown_arm_codes = sorted(set(used_arm_codes) - set(arm_by_code))
        if unknown_arm_codes:
            issues.append(
                self._issue(
                    first_row,
                    "Arm Code",
                    f"Unknown active Arm Code(s): {', '.join(unknown_arm_codes)}.",
                )
            )
        if len(set(used_arm_codes)) != 2:
            issues.append(
                self._issue(
                    first_row,
                    "Arm Code",
                    "NNG31 crossover master list must reference exactly two sequence arms.",
                )
            )
        issues.extend(
            self._build_period_issues(
                first_row=first_row,
                used_arm_codes=set(used_arm_codes),
                periods=periods,
            )
        )
        issues.extend(
            self._build_block_issues(
                first_row=first_row,
                parsed_rows=parsed_rows,
                used_arm_codes=set(used_arm_codes),
            )
        )
        return tuple(issues)

    def _build_period_issues(self, *, first_row, used_arm_codes, periods):
        values_by_arm = defaultdict(list)
        for period in periods:
            values_by_arm[str(period.arm.arm_code).strip()].append(period)
        issues = []
        treatment_sequences = []
        for arm_code in sorted(used_arm_codes):
            arm_periods = values_by_arm.get(arm_code, [])
            period_numbers = tuple(int(period.period_no) for period in arm_periods)
            if period_numbers != (1, 2):
                issues.append(
                    self._issue(
                        first_row,
                        "Arm Code",
                        f"Arm {arm_code} must configure contiguous Sequence Periods 1 and 2.",
                    )
                )
                continue
            if any(
                not str(period.treatment_code or "").strip()
                or period.start_event_definition_id is None
                or period.end_event_definition_id is None
                for period in arm_periods
            ):
                issues.append(
                    self._issue(
                        first_row,
                        "Arm Code",
                        f"Arm {arm_code} must define treatment, start event, and end event for both periods.",
                    )
                )
                continue
            treatment_sequences.append(
                tuple(str(period.treatment_code).strip() for period in arm_periods)
            )
        if len(treatment_sequences) == 2:
            first, second = treatment_sequences
            if len(set(first)) != 2 or second != tuple(reversed(first)):
                issues.append(
                    self._issue(
                        first_row,
                        "Arm Code",
                        "The two NNG31 arms must configure reverse two-treatment crossover sequences.",
                    )
                )
        return issues

    def _build_block_issues(self, *, first_row, parsed_rows, used_arm_codes):
        issues = []
        rows_by_block = defaultdict(list)
        for row in parsed_rows:
            rows_by_block[int(row.values["block_no"])].append(row)
        expected_block_numbers = list(range(1, len(EXPECTED_BLOCK_SIZES) + 1))
        if sorted(rows_by_block) != expected_block_numbers:
            issues.append(
                self._issue(
                    first_row,
                    "Block No",
                    f"Block No must be contiguous from 1 through {len(EXPECTED_BLOCK_SIZES)}.",
                )
            )
            return issues
        actual_sizes = tuple(len(rows_by_block[number]) for number in expected_block_numbers)
        if actual_sizes != EXPECTED_BLOCK_SIZES:
            issues.append(
                self._issue(
                    first_row,
                    "Block No",
                    "NNG31 requires five blocks of 4 followed by four blocks of 6.",
                )
            )
        expected_block_sequence = [
            block_no
            for block_no, block_size in enumerate(EXPECTED_BLOCK_SIZES, start=1)
            for _offset in range(block_size)
        ]
        if [int(row.values["block_no"]) for row in parsed_rows] != expected_block_sequence:
            issues.append(
                self._issue(
                    first_row,
                    "Block No",
                    "Each block must occupy one contiguous sequence range in block order.",
                )
            )
        if len(used_arm_codes) == 2:
            for block_no, block_rows in rows_by_block.items():
                counts = Counter(str(row.values["arm_code"]).strip() for row in block_rows)
                expected_per_arm = len(block_rows) // 2
                if any(counts[arm_code] != expected_per_arm for arm_code in used_arm_codes):
                    issues.append(
                        self._issue(
                            block_rows[0].row_number,
                            "Arm Code",
                            f"Block {block_no} is not balanced 1:1.",
                        )
                    )
            totals = Counter(
                str(row.values["arm_code"]).strip() for row in parsed_rows
            )
            if any(total != EXPECTED_RANDOMIZATION_TOTAL // 2 for total in totals.values()):
                issues.append(
                    self._issue(
                        first_row,
                        "Arm Code",
                        "NNG31 master list must allocate exactly 22 subjects to each sequence.",
                    )
                )
        return issues

    @staticmethod
    def _issue(row_number, column_label, reason):
        return RandomizationImportIssue(
            row_number=row_number,
            identifier="NNG31 master list",
            column_label=column_label,
            reason=str(_(reason)),
        )

    def validate_stored_configuration(self, *, study, scheme, arms, periods, slots):
        parsed_rows = tuple(
            RandomizationImportParsedRow(
                row_number=index + 2,
                identifier=str(slot.randomization_code or ""),
                values={
                    "scheme_code": scheme.code,
                    "randomization_code": str(slot.randomization_code or ""),
                    "sequence_no": slot.sequence_no,
                    "block_no": slot.block_no,
                    "arm_code": slot.arm.arm_code,
                },
            )
            for index, slot in enumerate(slots)
        )
        return self._build_configuration_issues(
            study=study,
            scheme=scheme,
            scheme_codes={str(scheme.code).strip()},
            parsed_rows=parsed_rows,
            arms=arms,
            periods=periods,
        )


class CommitNng31MasterListImportService:
    preview_service_class = PreviewNng31MasterListImportService
    repository_class = DjangoNng31MasterListRepository
    audit_adapter_class = AuditContextAdapter

    def __init__(
        self,
        preview_service=None,
        repository=None,
        audit_adapter=None,
        subject_slot_reconciler=None,
    ):
        self.preview_service = preview_service or self.preview_service_class()
        self.repository = repository or self.repository_class()
        self.audit_adapter = audit_adapter or self.audit_adapter_class()
        self.subject_slot_reconciler = (
            subject_slot_reconciler or self._reconcile_subject_slot_assignments
        )

    @staticmethod
    def _reconcile_subject_slot_assignments(*, assignments):
        from apps.subject.public import reconcile_imported_randomization_slots

        return reconcile_imported_randomization_slots(assignments=assignments)

    def _plan_existing_slot_rows(self, *, existing_slots, parsed_rows, arms_by_code):
        unused_rows = {
            row.values["sequence_no"]: row
            for row in parsed_rows
        }
        assigned_slot_rows = []
        assigned_slots = sorted(
            (
                slot
                for slot in existing_slots
                if slot.status == RandomizationSlotStatusChoice.ASSIGNED
            ),
            key=lambda slot: (slot.sequence_no, slot.pk),
        )
        for slot in assigned_slots:
            current_code = str(slot.randomization_code or "").strip()
            compatible_row = next(
                (
                    row
                    for row in unused_rows.values()
                    if current_code
                    and row.values["randomization_code"] == current_code
                    and arms_by_code[row.values["arm_code"]].pk == slot.arm_id
                ),
                None,
            )
            if compatible_row is None:
                compatible_row = next(
                    (
                        row
                        for row in unused_rows.values()
                        if arms_by_code[row.values["arm_code"]].pk == slot.arm_id
                    ),
                    None,
                )
            if compatible_row is None:
                raise RandomizationImportValidationError(
                    (
                        self.preview_service._issue(
                            1,
                            "Arm Code",
                            "The imported master list does not contain enough rows to preserve all assigned subjects in their current Arm.",
                        ),
                    )
                )
            assigned_slot_rows.append((slot, compatible_row))
            unused_rows.pop(compatible_row.values["sequence_no"])

        available_slots = sorted(
            (
                slot
                for slot in existing_slots
                if slot.status != RandomizationSlotStatusChoice.ASSIGNED
            ),
            key=lambda slot: (slot.sequence_no, slot.pk),
        )
        remaining_rows = sorted(
            unused_rows.values(),
            key=lambda row: row.values["sequence_no"],
        )
        return (*assigned_slot_rows, *zip(available_slots, remaining_rows, strict=True))

    @transaction.atomic
    def execute(self, command: CommitNng31MasterListCommand):
        preview_result = self.preview_service.execute(
            PreviewRandomizationImportCommand(
                actor_user_id=command.actor_user_id,
                study_id=command.study_id,
                file_name=command.file_name,
                file_content=command.file_content,
            )
        )
        if preview_result.issues:
            raise RandomizationImportValidationError(preview_result.issues)
        version = str(command.master_list_version or "").strip()
        if not version:
            raise RandomizationImportValidationError(
                (self.preview_service._issue(1, "Master-list Version", "Master-list version must not be blank."),)
            )
        scheme = self.repository.get_scheme(
            study_id=command.study_id,
            scheme_id=preview_result.scheme_id,
            for_update=True,
        )
        if scheme is None:
            raise RandomizationImportValidationError(
                (
                    self.preview_service._issue(
                        1,
                        "Scheme Code",
                        "The randomization scheme no longer exists.",
                    ),
                )
            )
        if scheme.master_list_locked_at is not None:
            raise RandomizationImportValidationError(
                (
                    self.preview_service._issue(
                        1,
                        "Scheme Code",
                        "The randomization master list is approved and locked; it cannot be replaced.",
                    ),
                )
            )
        arms_by_code = {
            str(arm.arm_code).strip(): arm
            for arm in self.repository.list_active_arms(scheme_id=scheme.pk)
        }
        existing_slots = list(
            self.repository.list_slots(scheme_id=scheme.pk, for_update=True)
        )
        configured_slots = [
            slot
            for slot in existing_slots
            if slot.status
            in (
                RandomizationSlotStatusChoice.ASSIGNED,
                RandomizationSlotStatusChoice.AVAILABLE,
            )
        ]
        retired_slots = [
            slot
            for slot in existing_slots
            if slot.status
            not in (
                RandomizationSlotStatusChoice.ASSIGNED,
                RandomizationSlotStatusChoice.AVAILABLE,
            )
        ]
        if len(configured_slots) not in (0, EXPECTED_RANDOMIZATION_TOTAL):
            raise RandomizationImportValidationError(
                (
                    self.preview_service._issue(
                        1,
                        "Randomization ID",
                        "Existing scheme must have no active slots or exactly 44 assigned/available slots.",
                    ),
                )
            )
        now = timezone.now()
        created_count = 0
        updated_count = 0
        assigned_metadata = ()
        with transaction.atomic():
            if configured_slots:
                planned_slot_rows = self._plan_existing_slot_rows(
                    existing_slots=configured_slots,
                    parsed_rows=preview_result.parsed_rows,
                    arms_by_code=arms_by_code,
                )
                assigned_metadata = self.repository.replace_existing_slots(
                    scheme=scheme,
                    slot_rows=[
                        (
                            slot,
                            {
                                **row.values,
                                "arm": arms_by_code[row.values["arm_code"]],
                            },
                        )
                        for slot, row in planned_slot_rows
                    ],
                    retired_slots=retired_slots,
                    now=now,
                )
                updated_count = len(planned_slot_rows)
                self.subject_slot_reconciler(assignments=assigned_metadata)
            else:
                if retired_slots:
                    self.repository.replace_existing_slots(
                        scheme=scheme,
                        slot_rows=[],
                        retired_slots=retired_slots,
                        now=now,
                    )
                for row in preview_result.parsed_rows:
                    values = row.values
                    defaults = {
                        "created_at": now,
                        "updated_at": now,
                        "deleted": False,
                        "arm": arms_by_code[values["arm_code"]],
                        "randomization_code": values["randomization_code"],
                        "block_no": values["block_no"],
                        "stratum_code": None,
                        "void_reason": None,
                        "status": RandomizationSlotStatusChoice.AVAILABLE,
                        "assigned_subject_id": None,
                        "assigned_event_id": None,
                        "assigned_at": None,
                    }
                    _slot, created = self.repository.update_or_create_slot(
                        scheme=scheme,
                        sequence_no=values["sequence_no"],
                        defaults=defaults,
                    )
                    created_count += int(created)
                    updated_count += int(not created)

            scheme.master_list_version = version
            scheme.master_list_checksum = preview_result.checksum
            scheme.master_list_source_filename = Path(command.file_name).name
            scheme.master_list_imported_by_id = command.actor_user_id
            scheme.master_list_imported_at = now
            scheme.master_list_approved_by_id = None
            scheme.master_list_approved_at = None
            scheme.master_list_locked_at = None
            scheme.updated_at = now
            self.repository.save_scheme(
                scheme,
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
                ],
            )
            self.audit_adapter.record_event(
                action="randomization_master_list_imported",
                object_type="randomization_scheme",
                object_id=scheme.pk,
                actor_user_id=command.actor_user_id,
                after_data={
                    "version": version,
                    "checksum_sha256": preview_result.checksum,
                    "source_filename": scheme.master_list_source_filename,
                    "slot_count": preview_result.total_rows,
                    "assigned_slot_bypass_count": len(assigned_metadata),
                    "assigned_slot_mappings": list(assigned_metadata),
                    "retired_surplus_slot_count": len(retired_slots),
                },
            )
        return CommitNng31MasterListResult(
            total_rows=preview_result.total_rows,
            created_count=created_count,
            updated_count=updated_count,
            scheme_id=scheme.pk,
            checksum=preview_result.checksum,
            master_list_version=version,
            assigned_bypass_count=len(assigned_metadata),
        )


class ApproveNng31MasterListService:
    preview_service_class = PreviewNng31MasterListImportService
    repository_class = DjangoNng31MasterListRepository
    audit_adapter_class = AuditContextAdapter

    def __init__(self, preview_service=None, repository=None, audit_adapter=None):
        self.preview_service = preview_service or self.preview_service_class()
        self.repository = repository or self.repository_class()
        self.audit_adapter = audit_adapter or self.audit_adapter_class()

    @transaction.atomic
    def execute(self, command: ApproveNng31MasterListCommand):
        study = self.repository.get_study(study_id=command.study_id)
        scheme = self.repository.get_scheme(
            study_id=command.study_id,
            scheme_id=command.scheme_id,
            for_update=True,
        )
        if study is None or scheme is None:
            raise RandomizationImportValidationError(
                (self.preview_service._issue(1, "Scheme Code", "Study or scheme was not found."),)
            )
        if scheme.master_list_locked_at is not None:
            raise RandomizationImportValidationError(
                (self.preview_service._issue(1, "Scheme Code", "The master list is already approved and locked."),)
            )
        expected_checksum = str(command.expected_checksum or "").strip().lower()
        current_checksum = str(scheme.master_list_checksum or "").strip().lower()
        if not current_checksum or expected_checksum != current_checksum:
            raise RandomizationImportValidationError(
                (self.preview_service._issue(1, "Checksum", "Expected checksum does not match the imported master list."),)
            )
        if scheme.master_list_imported_by_id == command.actor_user_id:
            raise RandomizationImportValidationError(
                (self.preview_service._issue(1, "Approver", "Importer and approver must be different users."),)
            )
        arms = list(self.repository.list_active_arms(scheme_id=scheme.pk))
        periods = list(self.repository.list_sequence_periods(scheme_id=scheme.pk))
        slots = list(self.repository.list_slots(scheme_id=scheme.pk))
        issues = self.preview_service.validate_stored_configuration(
            study=study,
            scheme=scheme,
            arms=arms,
            periods=periods,
            slots=slots,
        )
        if issues:
            raise RandomizationImportValidationError(issues)

        now = timezone.now()
        with transaction.atomic():
            scheme.master_list_approved_by_id = command.actor_user_id
            scheme.master_list_approved_at = now
            scheme.master_list_locked_at = now
            scheme.approved_by_id = command.actor_user_id
            scheme.updated_at = now
            self.repository.save_scheme(
                scheme,
                update_fields=[
                    "master_list_approved_by_id",
                    "master_list_approved_at",
                    "master_list_locked_at",
                    "approved_by_id",
                    "updated_at",
                ],
            )
            self.audit_adapter.record_event(
                action="randomization_master_list_approved",
                object_type="randomization_scheme",
                object_id=scheme.pk,
                actor_user_id=command.actor_user_id,
                after_data={
                    "version": scheme.master_list_version,
                    "checksum_sha256": scheme.master_list_checksum,
                    "locked_at": now,
                },
            )
        return ApproveNng31MasterListResult(
            scheme_id=scheme.pk,
            checksum=scheme.master_list_checksum,
        )


__all__ = [
    "ApproveNng31MasterListService",
    "CommitNng31MasterListImportService",
    "EXPECTED_BLOCK_SIZES",
    "EXPECTED_RANDOMIZATION_TOTAL",
    "Nng31MasterListPreviewResult",
    "PreviewNng31MasterListImportService",
]
