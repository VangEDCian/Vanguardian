from __future__ import annotations

import abc
from abc import abstractmethod
from dataclasses import dataclass, replace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.choices.study import RandomizationSchemeStatusChoice
from apps.study.application.services.randomization_slot_generation import (
    StudyRandomizationSlotGenerationService,
)
from apps.study.application.use_cases.randomization_import_preview import (
    RandomizationArmImportPreviewUseCase,
    RandomizationImportIssue,
    RandomizationImportPreviewResult,
    RandomizationSchemeImportPreviewUseCase,
)
from apps.study.infrastructure.persistence.models import RandomizationArm, RandomizationScheme


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


class BaseRandomizationImportValidationService(abc.ABC):
    model_validation_exclude_fields: tuple[str, ...] = ()

    @staticmethod
    def _resolve_scheme_status(*, values, existing_scheme=None):
        imported_status = BaseRandomizationImportValidationService._optional_value(values, "status")
        if imported_status is not None:
            return imported_status
        if existing_scheme is not None:
            return getattr(existing_scheme, "status", RandomizationSchemeStatusChoice.DRAFT)
        return RandomizationSchemeStatusChoice.DRAFT

    @staticmethod
    def _append_issues(preview_result, issues):
        if not issues:
            return preview_result
        return replace(
            preview_result,
            issues=tuple([*preview_result.issues, *issues]),
        )

    @staticmethod
    def _optional_value(values, key):
        value = values.get(key)
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @staticmethod
    def _column_labels(preview_result):
        return {column.key: column.label for column in preview_result.columns}

    def _validate_model_instance(self, *, parsed_row, model_instance, preview_result):
        try:
            model_instance.full_clean(exclude=self.model_validation_exclude_fields)
            return ()
        except ValidationError as exc:
            label_map = self._column_labels(preview_result)
            issues = []
            if hasattr(exc, "message_dict") and exc.message_dict:
                for field_name, messages in exc.message_dict.items():
                    column_label = label_map.get(field_name, field_name.replace("_", " ").title())
                    for message in messages:
                        issues.append(
                            RandomizationImportIssue(
                                row_number=parsed_row.row_number,
                                identifier=parsed_row.identifier,
                                column_label=column_label,
                                reason=str(message),
                            )
                        )
            else:
                for message in exc.messages:
                    issues.append(
                        RandomizationImportIssue(
                            row_number=parsed_row.row_number,
                            identifier=parsed_row.identifier,
                            column_label="Row",
                            reason=str(message),
                        )
                    )
            return tuple(issues)

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError('Must be implement method when extended')


class PreviewStudyRandomizationSchemesImportService(BaseRandomizationImportValidationService):
    preview_use_case_class = RandomizationSchemeImportPreviewUseCase
    randomization_scheme_model = RandomizationScheme

    def __init__(self, preview_use_case=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()

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
            str(scheme.code).strip().lower(): scheme
            for scheme in self.randomization_scheme_model.objects.filter(
                study_id=study_id,
            )
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
                candidate = self.randomization_scheme_model(
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
    randomization_scheme_model = RandomizationScheme
    randomization_arm_model = RandomizationArm
    model_validation_exclude_fields = ("scheme",)

    def __init__(self, preview_use_case=None):
        self.preview_use_case = preview_use_case or self.preview_use_case_class()

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
        schemes = self.randomization_scheme_model.objects.filter(
            study_id=study_id,
            deleted=False,
        )
        return {str(scheme.code).strip().lower(): scheme for scheme in schemes}

    def _build_existing_arm_map(self, *, study_id):
        arms = self.randomization_arm_model.objects.select_related("scheme").filter(
            scheme__study_id=study_id,
            scheme__deleted=False,
            deleted=False,
        )
        return {
            (str(arm.scheme.code).strip().lower(), str(arm.arm_code).strip().lower()): arm
            for arm in arms
        }

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
                candidate = self.randomization_arm_model(
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

class CommitStudyRandomizationSchemesImportService(BaseRandomizationImportValidationService):
    preview_service_class = PreviewStudyRandomizationSchemesImportService
    randomization_scheme_model = RandomizationScheme
    randomization_arm_model = RandomizationArm
    slot_generation_service_class = StudyRandomizationSlotGenerationService

    def __init__(self, preview_service=None, slot_generation_service=None):
        self.preview_service = preview_service or self.preview_service_class()
        self.slot_generation_service = (
            slot_generation_service or self.slot_generation_service_class()
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
                outcome, scheme = self._upsert_scheme(
                    study_id=command.study_id,
                    parsed_row=parsed_row,
                    actor_user_id=command.actor_user_id,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                else:
                    updated_count += 1
                self._generate_slots_for_active_scheme(scheme)

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
            scheme = self.randomization_scheme_model.objects.create(
                study_id=study_id,
                code=values["code"],
                approved_by_id=None,
                created_at=now,
                created_by_id=actor_user_id,
                **defaults,
            )
            return "created", scheme

        for field_name, value in defaults.items():
            setattr(scheme, field_name, value)
        scheme.save(update_fields=list(defaults.keys()))
        return "updated", scheme

    def _generate_slots_for_active_scheme(self, scheme):
        if getattr(scheme, "status", None) != RandomizationSchemeStatusChoice.ACTIVE:
            return

        active_arms = self.randomization_arm_model.objects.filter(
            scheme_id=scheme.pk,
            deleted=False,
            is_active=True,
        )
        for arm in active_arms:
            self.slot_generation_service.generate_slots_for_scheme_arm(
                scheme=scheme,
                arm=arm,
            )


class CommitStudyRandomizationArmsImportService(BaseRandomizationImportValidationService):
    preview_service_class = PreviewStudyRandomizationArmsImportService
    randomization_scheme_model = RandomizationScheme
    randomization_arm_model = RandomizationArm
    slot_generation_service_class = StudyRandomizationSlotGenerationService

    def __init__(self, preview_service=None, slot_generation_service=None):
        self.preview_service = preview_service or self.preview_service_class()
        self.slot_generation_service = (
            slot_generation_service or self.slot_generation_service_class()
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

        with transaction.atomic():
            for parsed_row in preview_result.parsed_rows:
                outcome, scheme, arm = self._upsert_arm(
                    parsed_row=parsed_row,
                    scheme_map=scheme_map,
                    now=now,
                )
                if outcome == "created":
                    created_count += 1
                else:
                    updated_count += 1
                self._generate_slots_for_active_arm(scheme=scheme, arm=arm)

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
            arm = self.randomization_arm_model.objects.create(
                scheme=scheme,
                arm_code=values["arm_code"],
                current_count=0,
                created_at=now,
                **defaults,
            )
            return "created", scheme, arm

        for field_name, value in defaults.items():
            setattr(arm, field_name, value)
        arm.save(update_fields=list(defaults.keys()))
        return "updated", scheme, arm

    def _generate_slots_for_active_arm(self, *, scheme, arm):
        if getattr(scheme, "status", None) != RandomizationSchemeStatusChoice.ACTIVE:
            return
        if not getattr(arm, "is_active", False):
            return

        self.slot_generation_service.generate_slots_for_scheme_arm(
            scheme=scheme,
            arm=arm,
        )
