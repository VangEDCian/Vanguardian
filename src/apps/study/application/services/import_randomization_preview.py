from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.study.application.commands.import_randomization.types import PreviewRandomizationImportCommand
from apps.study.application.services.import_randomization_base import BaseRandomizationImportValidationService
from apps.study.application.use_cases.randomization_import_preview import (
    RandomizationArmImportPreviewUseCase,
    RandomizationImportIssue,
    RandomizationImportPreviewResult,
    RandomizationSchemeImportPreviewUseCase,
)
from apps.study.infrastructure.repositories import DjangoRandomizationRepository


class PreviewStudyRandomizationSchemesImportService(BaseRandomizationImportValidationService):
    preview_use_case_class = RandomizationSchemeImportPreviewUseCase
    repository_class = DjangoRandomizationRepository

    def __init__(self, preview_use_case=None, repository=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()
        self.repository = repository or self.repository_class()

    def execute(self, command: PreviewRandomizationImportCommand) -> RandomizationImportPreviewResult:
        preview_result = self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )
        model_issues = self._build_model_validation_issues(
            study_id=command.study_id,
            parsed_rows=preview_result.parsed_rows,
            preview_result=preview_result,
        )
        return self._append_issues(preview_result, model_issues)

    def _build_model_validation_issues(self, *, study_id, parsed_rows, preview_result):
        if not parsed_rows:
            return ()

        existing_scheme_map = {
            str(scheme.code).strip().lower(): scheme for scheme in self.repository.list_schemes(study_id=study_id)
        }
        now = timezone.now()
        issues = []
        for parsed_row in parsed_rows:
            values = parsed_row.values
            scheme_code_normalized = str(values.get("code", "")).strip().lower()
            existing_scheme = existing_scheme_map.get(scheme_code_normalized)
            candidate_defaults = {
                "study_id": study_id,
                "code": values["code"],
                "name": values["name"],
                "randomization_type": values["randomization_type"],
                "allocation_ratio_json": self._optional_value(values, "allocation_ratio_json"),
                "target_randomized_total": values["target_randomized_total"],
                "eligibility_rule_code": self._optional_value(values, "eligibility_rule_code"),
                "requires_screening_pass": values["requires_screening_pass"],
                "is_open_label": values["is_open_label"],
                "status": self._resolve_scheme_status(values=values, existing_scheme=existing_scheme),
                "effective_from": self._optional_value(values, "effective_from"),
                "effective_to": self._optional_value(values, "effective_to"),
                "updated_at": now,
                "deleted": False,
                "notes": self._optional_value(values, "notes"),
            }
            if existing_scheme is not None:
                for field_name, field_value in candidate_defaults.items():
                    setattr(existing_scheme, field_name, field_value)
                candidate = existing_scheme
            else:
                candidate = self.repository.build_scheme(
                    **candidate_defaults,
                    created_at=now,
                )
            issues.extend(
                self._validate_model_instance(
                    parsed_row=parsed_row,
                    model_instance=candidate,
                    preview_result=preview_result,
                )
            )
            issues.extend(
                self._build_effective_window_issues(
                    parsed_row=parsed_row,
                    preview_result=preview_result,
                )
            )

        return tuple(issues)

    def _build_effective_window_issues(self, *, parsed_row, preview_result):
        values = parsed_row.values
        effective_from = self._optional_value(values, "effective_from")
        effective_to = self._optional_value(values, "effective_to")
        if not effective_from or not effective_to:
            return ()

        if effective_to >= effective_from:
            return ()

        return (
            RandomizationImportIssue(
                row_number=parsed_row.row_number,
                identifier=parsed_row.identifier,
                column_label=self._column_labels(preview_result).get("effective_to", "Effective To"),
                reason=str(_("Effective To must be greater than or equal to Effective From.")),
            ),
        )


class PreviewStudyRandomizationArmsImportService(BaseRandomizationImportValidationService):
    preview_use_case_class = RandomizationArmImportPreviewUseCase
    repository_class = DjangoRandomizationRepository
    model_validation_exclude_fields = ("scheme",)

    def __init__(self, preview_use_case=None, repository=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()
        self.repository = repository or self.repository_class()

    def execute(self, command: PreviewRandomizationImportCommand) -> RandomizationImportPreviewResult:
        preview_result = self.preview_use_case.execute(
            file_name=command.file_name,
            file_content=command.file_content,
        )
        scheme_map = self._build_scheme_map(study_id=command.study_id)
        existing_arm_map = self._build_existing_arm_map(study_id=command.study_id)
        issues = [
            *self._build_missing_scheme_issues(
                parsed_rows=preview_result.parsed_rows,
                scheme_map=scheme_map,
            ),
            *self._build_model_validation_issues(
                preview_result=preview_result,
                scheme_map=scheme_map,
                existing_arm_map=existing_arm_map,
            ),
        ]
        return self._append_issues(preview_result, tuple(issues))

    def _build_scheme_map(self, *, study_id):
        return self.repository.list_active_scheme_map(study_id=study_id)

    def _build_existing_arm_map(self, *, study_id):
        return self.repository.list_arm_map(study_id=study_id)

    def _build_missing_scheme_issues(self, *, parsed_rows, scheme_map):
        if not parsed_rows:
            return ()

        issues = []
        for row in parsed_rows:
            scheme_code = str(row.values.get("scheme_code", "")).strip()
            if scheme_code.lower() in scheme_map:
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

    def _build_model_validation_issues(self, *, preview_result, scheme_map, existing_arm_map):
        if not preview_result.parsed_rows:
            return ()

        now = timezone.now()
        issues = []
        for parsed_row in preview_result.parsed_rows:
            values = parsed_row.values
            scheme_code = str(values.get("scheme_code", "")).strip().lower()
            scheme = scheme_map.get(scheme_code)
            if scheme is None:
                continue

            arm_key = (scheme_code, str(values.get("arm_code", "")).strip().lower())
            existing_arm = existing_arm_map.get(arm_key)
            current_count = getattr(existing_arm, "current_count", 0)
            is_active = self._optional_value(values, "is_active")
            candidate_defaults = {
                "scheme": scheme,
                "arm_code": values["arm_code"],
                "arm_name": values["arm_name"],
                "target_count": values["target_count"],
                "current_count": current_count,
                "display_order": values["display_order"],
                "is_active": is_active if is_active is not None else True,
                "notes": self._optional_value(values, "notes"),
                "updated_at": now,
                "deleted": False,
            }
            if existing_arm is not None:
                for field_name, field_value in candidate_defaults.items():
                    setattr(existing_arm, field_name, field_value)
                candidate = existing_arm
            else:
                candidate = self.repository.build_arm(
                    **candidate_defaults,
                    created_at=now,
                )
            issues.extend(
                self._validate_model_instance(
                    parsed_row=parsed_row,
                    model_instance=candidate,
                    preview_result=preview_result,
                )
            )

            target_count = values.get("target_count")
            if target_count is not None and target_count < current_count:
                issues.append(
                    RandomizationImportIssue(
                        row_number=parsed_row.row_number,
                        identifier=parsed_row.identifier,
                        column_label=self._column_labels(preview_result).get("target_count", "Target Count"),
                        reason=str(
                            _(
                                "Target Count cannot be smaller than the current assigned count (%(current_count)s).",
                            )
                            % {"current_count": current_count}
                        ),
                    )
                )

        return tuple(issues)
