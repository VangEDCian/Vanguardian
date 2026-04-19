from __future__ import annotations

from dataclasses import dataclass, replace

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.study.infrastructure.persistence.models import RandomizationArm, RandomizationScheme
from apps.study.application.use_cases.randomization_import_preview import (
    RandomizationArmImportPreviewUseCase,
    RandomizationImportIssue,
    RandomizationImportPreviewResult,
    RandomizationSchemeImportPreviewUseCase,
)


@dataclass(frozen=True)
class PreviewRandomizationImportCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CommitRandomizationImportCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class CommitRandomizationImportResult:
    total_rows: int
    created_count: int
    updated_count: int


class RandomizationImportValidationError(Exception):
    """Raised when the uploaded file contains row-level validation issues."""

    def __init__(self, issues: tuple[RandomizationImportIssue, ...]):
        super().__init__(str(_("The uploaded file contains validation issues.")))
        self.issues = issues


class PreviewStudyRandomizationSchemesImportService:
    preview_use_case_class = RandomizationSchemeImportPreviewUseCase

    def __init__(self, preview_use_case=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()

    def execute(self, command: PreviewRandomizationImportCommand) -> RandomizationImportPreviewResult:
        return self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )


class PreviewStudyRandomizationArmsImportService:
    preview_use_case_class = RandomizationArmImportPreviewUseCase
    randomization_scheme_model = RandomizationScheme

    def __init__(self, preview_use_case=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()

    def execute(self, command: PreviewRandomizationImportCommand) -> RandomizationImportPreviewResult:
        preview_result = self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )
        missing_scheme_issues = self._build_missing_scheme_issues(
            study_id=command.study_id,
            preview_result=preview_result,
        )
        if not missing_scheme_issues:
            return preview_result

        return replace(
            preview_result,
            issues=tuple([*preview_result.issues, *missing_scheme_issues]),
        )

    def _build_missing_scheme_issues(self, *, study_id, preview_result):
        parsed_rows = preview_result.parsed_rows
        if not parsed_rows:
            return ()

        existing_scheme_codes = {
            str(code).strip().lower()
            for code in self.randomization_scheme_model.objects.filter(
                study_id=study_id,
                deleted=False,
            ).values_list("code", flat=True)
        }

        issues = []
        for row in parsed_rows:
            scheme_code = str(row.values.get("scheme_code", "")).strip()
            if scheme_code.lower() in existing_scheme_codes:
                continue
            issues.append(
                RandomizationImportIssue(
                    row_number=row.row_number,
                    identifier=row.identifier,
                    column_label="Scheme Code",
                    reason=str(
                        _("Scheme code %(scheme_code)s was not found in this study.")
                        % {"scheme_code": scheme_code}
                    ),
                )
            )
        return tuple(issues)


class CommitStudyRandomizationSchemesImportService:
    preview_use_case_class = RandomizationSchemeImportPreviewUseCase
    randomization_scheme_model = RandomizationScheme

    def __init__(self, preview_use_case=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()

    def execute(self, command: CommitRandomizationImportCommand) -> CommitRandomizationImportResult:
        preview_result = self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )
        if preview_result.issues:
            raise RandomizationImportValidationError(preview_result.issues)

        created_count = 0
        updated_count = 0
        now = timezone.now()

        with transaction.atomic():
            for parsed_row in preview_result.parsed_rows:
                outcome = self._upsert_scheme(
                    study_id=command.study_id,
                    parsed_row=parsed_row,
                    actor_user_id=command.actor_user_id,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                else:
                    updated_count += 1

        return CommitRandomizationImportResult(
            total_rows=preview_result.total_rows,
            created_count=created_count,
            updated_count=updated_count,
        )

    def _upsert_scheme(self, *, study_id, parsed_row, actor_user_id, now):
        values = parsed_row.values
        scheme = self.randomization_scheme_model.objects.filter(
            study_id=study_id,
            code__iexact=values["code"],
        ).first()

        defaults = {
            "name": values["name"],
            "randomization_type": values["randomization_type"],
            "target_randomized_total": values["target_randomized_total"],
            "eligibility_rule_code": values["eligibility_rule_code"] or None,
            "requires_screening_pass": values["requires_screening_pass"],
            "is_open_label": values["is_open_label"],
            "deleted": False,
            "updated_at": now,
        }

        if scheme is None:
            self.randomization_scheme_model.objects.create(
                study_id=study_id,
                code=values["code"],
                status="draft",
                allocation_ratio_json=None,
                effective_from=None,
                effective_to=None,
                approved_by_id=None,
                notes=None,
                created_at=now,
                created_by_id=actor_user_id,
                **defaults,
            )
            return "created"

        for field_name, value in defaults.items():
            setattr(scheme, field_name, value)
        scheme.save(update_fields=list(defaults.keys()))
        return "updated"


class CommitStudyRandomizationArmsImportService:
    preview_service_class = PreviewStudyRandomizationArmsImportService
    randomization_scheme_model = RandomizationScheme
    randomization_arm_model = RandomizationArm

    def __init__(self, preview_service=None):
        self.preview_service = preview_service or self.preview_service_class()

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

        with transaction.atomic():
            for parsed_row in preview_result.parsed_rows:
                outcome = self._upsert_arm(
                    parsed_row=parsed_row,
                    scheme_map=scheme_map,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                else:
                    updated_count += 1

        return CommitRandomizationImportResult(
            total_rows=preview_result.total_rows,
            created_count=created_count,
            updated_count=updated_count,
        )

    def _build_scheme_map(self, *, study_id):
        schemes = self.randomization_scheme_model.objects.filter(
            study_id=study_id,
            deleted=False,
        )
        return {str(scheme.code).strip().lower(): scheme for scheme in schemes}

    def _upsert_arm(self, *, parsed_row, scheme_map, now):
        values = parsed_row.values
        scheme = scheme_map[str(values["scheme_code"]).strip().lower()]
        arm = self.randomization_arm_model.objects.filter(
            scheme_id=scheme.pk,
            arm_code__iexact=values["arm_code"],
        ).first()

        defaults = {
            "arm_name": values["arm_name"],
            "target_count": values["target_count"],
            "display_order": values["display_order"],
            "is_active": True,
            "deleted": False,
            "updated_at": now,
        }

        if arm is None:
            self.randomization_arm_model.objects.create(
                scheme=scheme,
                arm_code=values["arm_code"],
                current_count=0,
                notes=None,
                created_at=now,
                **defaults,
            )
            return "created"

        for field_name, value in defaults.items():
            setattr(arm, field_name, value)
        arm.save(update_fields=list(defaults.keys()))
        return "updated"
