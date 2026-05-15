from django.db import transaction
from django.utils import timezone

from apps.study.application.commands.import_randomization.types import (
    CommitRandomizationImportCommand,
    CommitRandomizationImportResult,
    PreviewRandomizationImportCommand,
    RandomizationImportValidationError,
)
from apps.study.application.services.import_randomization_base import BaseRandomizationImportValidationService
from apps.study.application.services.import_randomization_preview import (
    PreviewStudyRandomizationArmsImportService,
    PreviewStudyRandomizationSchemesImportService,
)
from apps.study.application.services.randomization_audit import (
    StudyRandomizationImportAuditService,
    serialize_randomization_arm_snapshot,
    serialize_randomization_scheme_snapshot,
)
from apps.study.application.services.randomization_slot_generation import (
    RandomizationSlotGenerationError,
    StudyRandomizationSlotGenerationService,
)
from apps.study.application.use_cases.randomization_import_preview import RandomizationImportIssue
from apps.study.domain import RandomizationScheme
from apps.study.infrastructure.repositories import DjangoRandomizationRepository


class CommitStudyRandomizationSchemesImportService(BaseRandomizationImportValidationService):
    preview_service_class = PreviewStudyRandomizationSchemesImportService
    repository_class = DjangoRandomizationRepository
    slot_generation_service_class = StudyRandomizationSlotGenerationService
    randomization_audit_service_class = StudyRandomizationImportAuditService

    def __init__(
        self,
        preview_service=None,
        slot_generation_service=None,
        randomization_audit_service=None,
        repository=None,
    ):
        self.repository = repository or self.repository_class()
        self.preview_service = preview_service or self.preview_service_class()
        self.slot_generation_service = (
            slot_generation_service or self.slot_generation_service_class()
        )
        self.randomization_audit_service = (
            randomization_audit_service or self.randomization_audit_service_class()
        )

    def execute(self, command: CommitRandomizationImportCommand) -> CommitRandomizationImportResult:
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

        created_count = 0
        updated_count = 0
        now = timezone.now()

        with transaction.atomic():
            for parsed_row in preview_result.parsed_rows:
                outcome, scheme, before_data = self._upsert_scheme(
                    study_id=command.study_id,
                    parsed_row=parsed_row,
                    actor_user_id=command.actor_user_id,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                    self.randomization_audit_service.record_scheme_inserted_by_import(
                        scheme=scheme,
                        actor_user_id=command.actor_user_id,
                    )
                else:
                    updated_count += 1
                    self.randomization_audit_service.record_scheme_updated_by_import(
                        scheme=scheme,
                        actor_user_id=command.actor_user_id,
                        before_data=before_data,
                    )
                self._generate_slots_for_active_scheme(scheme)

        return CommitRandomizationImportResult(
            total_rows=preview_result.total_rows,
            created_count=created_count,
            updated_count=updated_count,
        )

    def _upsert_scheme(self, *, study_id, parsed_row, actor_user_id, now):
        values = parsed_row.values
        scheme = self.repository.get_scheme_by_code(
            study_id=study_id,
            code=values["code"],
        )

        defaults = {
            "name": values["name"],
            "randomization_type": values["randomization_type"],
            "allocation_ratio_json": self._optional_value(values, "allocation_ratio_json"),
            "target_randomized_total": values["target_randomized_total"],
            "eligibility_rule_code": self._optional_value(values, "eligibility_rule_code"),
            "requires_screening_pass": values["requires_screening_pass"],
            "is_open_label": values["is_open_label"],
            "status": self._resolve_scheme_status(values=values, existing_scheme=scheme),
            "effective_from": self._optional_value(values, "effective_from"),
            "effective_to": self._optional_value(values, "effective_to"),
            "notes": self._optional_value(values, "notes"),
            "deleted": False,
            "updated_at": now,
        }

        if scheme is None:
            scheme = self.repository.create_scheme(
                study_id=study_id,
                code=values["code"],
                approved_by_id=None,
                created_at=now,
                created_by_id=actor_user_id,
                **defaults,
            )
            return "created", scheme, {}

        before_data = serialize_randomization_scheme_snapshot(scheme)
        for field_name, value in defaults.items():
            setattr(scheme, field_name, value)
        self.repository.save_scheme(scheme, update_fields=list(defaults.keys()))
        return "updated", scheme, before_data

    def _generate_slots_for_active_scheme(self, scheme):
        if not RandomizationScheme.is_active(getattr(scheme, "status", None)):
            return

        active_arms = self.repository.list_active_arms_for_scheme(
            scheme_id=scheme.pk,
        )
        for arm in active_arms:
            self.slot_generation_service.generate_slots_for_scheme_arm(
                scheme=scheme,
                arm=arm,
            )


class CommitStudyRandomizationArmsImportService(BaseRandomizationImportValidationService):
    preview_service_class = PreviewStudyRandomizationArmsImportService
    repository_class = DjangoRandomizationRepository
    slot_generation_service_class = StudyRandomizationSlotGenerationService
    randomization_audit_service_class = StudyRandomizationImportAuditService

    def __init__(
        self,
        preview_service=None,
        slot_generation_service=None,
        randomization_audit_service=None,
        repository=None,
    ):
        self.repository = repository or self.repository_class()
        self.preview_service = preview_service or self.preview_service_class()
        self.slot_generation_service = (
            slot_generation_service or self.slot_generation_service_class()
        )
        self.randomization_audit_service = (
            randomization_audit_service or self.randomization_audit_service_class()
        )

    def execute(self, command: CommitRandomizationImportCommand) -> CommitRandomizationImportResult:
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

        created_count = 0
        updated_count = 0
        now = timezone.now()
        scheme_map = self._build_scheme_map(study_id=command.study_id)
        impacted_schemes: dict[int, tuple[object, object]] = {}
        pending_audits: list[tuple[str, object, object]] = []

        with transaction.atomic():
            for parsed_row in preview_result.parsed_rows:
                outcome, scheme, arm, before_data = self._upsert_arm(
                    parsed_row=parsed_row,
                    scheme_map=scheme_map,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                    pending_audits.append(("created", arm, None))
                else:
                    updated_count += 1
                    pending_audits.append(("updated", arm, before_data))
                impacted_schemes[scheme.pk] = (scheme, parsed_row)

            for scheme, parsed_row in impacted_schemes.values():
                self._generate_slots_for_impacted_scheme(
                    scheme=scheme,
                    parsed_row=parsed_row,
                )
            for outcome, arm, before_data in pending_audits:
                if outcome == "created":
                    self.randomization_audit_service.record_arm_inserted_by_import(
                        arm=arm,
                        actor_user_id=command.actor_user_id,
                    )
                else:
                    self.randomization_audit_service.record_arm_updated_by_import(
                        arm=arm,
                        actor_user_id=command.actor_user_id,
                        before_data=before_data,
                    )

        return CommitRandomizationImportResult(
            total_rows=preview_result.total_rows,
            created_count=created_count,
            updated_count=updated_count,
        )

    def _build_scheme_map(self, *, study_id):
        return self.repository.list_active_scheme_map(study_id=study_id)

    def _upsert_arm(self, *, parsed_row, scheme_map, now):
        values = parsed_row.values
        scheme = scheme_map[str(values["scheme_code"]).strip().lower()]
        arm = self.repository.get_arm_by_code(
            scheme_id=scheme.pk,
            arm_code=values["arm_code"],
        )
        is_active = self._optional_value(values, "is_active")

        defaults = {
            "arm_name": values["arm_name"],
            "target_count": values["target_count"],
            "display_order": values["display_order"],
            "is_active": is_active if is_active is not None else True,
            "notes": self._optional_value(values, "notes"),
            "deleted": False,
            "updated_at": now,
        }

        if arm is None:
            arm = self.repository.create_arm(
                scheme=scheme,
                arm_code=values["arm_code"],
                current_count=0,
                created_at=now,
                **defaults,
            )
            return "created", scheme, arm, {}

        before_data = serialize_randomization_arm_snapshot(arm)
        for field_name, value in defaults.items():
            setattr(arm, field_name, value)
        self.repository.save_arm(arm, update_fields=list(defaults.keys()))
        return "updated", scheme, arm, before_data

    def _generate_slots_for_impacted_scheme(self, *, scheme, parsed_row):
        if not RandomizationScheme.is_active(getattr(scheme, "status", None)):
            return

        active_arms = list(
            self.repository.list_active_arms_for_scheme(
                scheme_id=scheme.pk,
            ),
        )
        if not active_arms:
            return

        try:
            self.slot_generation_service.generate_slots_for_scheme_arm(
                scheme=scheme,
                arm=active_arms[0],
            )
        except RandomizationSlotGenerationError as exc:
            raise RandomizationImportValidationError(
                (
                    RandomizationImportIssue(
                        row_number=parsed_row.row_number,
                        identifier=parsed_row.identifier,
                        column_label="Scheme Code",
                        reason=str(exc),
                    ),
                ),
            ) from exc
