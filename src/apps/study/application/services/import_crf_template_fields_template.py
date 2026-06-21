from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from apps.core.choices.datacapture import DataCaptureFieldReviewTypeChoices
from apps.crf.domain.exceptions import FormBuilderDomainValidationError, StudyScopeViolationError
from apps.crf.public import CrfContextAdapter
from apps.study.application.commands.import_crf_template_fields_template import (
    CrfTemplateFieldImportIssue,
    ImportStudyCrfTemplateFieldsTemplateCommand,
    ImportStudyCrfTemplateFieldsTemplateResult,
)
from apps.study.application.commands.import_crf_templates_template import CrfTemplateImportFormatError
from apps.study.application.commands.import_crf_templates_template.workbook import CrfTemplateWorkbookMixin


@dataclass(frozen=True)
class _PreparedTemplateFieldImportRow:
    row_number: int
    identifier: str
    form_template: object
    section_template: object
    payload: dict


class ImportStudyCrfTemplateFieldsTemplateService(CrfTemplateWorkbookMixin):
    crf_context_adapter_class = CrfContextAdapter
    template_fields_sheet_name = "Template Fields"
    expected_columns = {
        template_fields_sheet_name: (
            "Form Name",
            "Section Name",
            "Field Name",
            "Field Description Vi",
            "Field Description En",
            "Data Type",
            "Display Order",
            "Control Type",
            "Control Layout",
            "Layout",
            "Behavior",
            "Style",
            "Classes",
            "Text Hint Vi",
            "Text Hint En",
            "Options Vi",
            "Options En",
            "SDTM",
            "Range Min",
            "Range Max",
            "Precision",
            "Allowed Missing Value",
            "Data Sementic",
            "Max Length",
            "Min Length",
            "Pattern Validator",
            "Validators Err Mesage Vi",
            "Validators Err Mesage En",
            "Unit Vi",
            "Unit En",
            "Codelist Vi",
            "Codelist En",
            "Comments Vi",
            "Comments En",
            "Review Study Version",
            "Review Type",
            "Review Required For Verify",
            "Review Required For Lock",
            "Review Blocking If Missing",
            "Review Role Required",
            "Review Enabled",
        ),
    }
    expected_header_map = {
        template_fields_sheet_name: {
            "form name": "form_name",
            "section name": "section_name",
            "field name": "field_name",
            "field description vi": "field_description_vi",
            "field description en": "field_description_en",
            "data type": "data_type",
            "display order": "display_order",
            "control type": "control_type",
            "control layout": "control_layout",
            "layout": "layout",
            "behavior": "behavior",
            "style": "style",
            "classes": "classes",
            "text hint vi": "text_vi",
            "text hint en": "text_en",
            "options vi": "options_vi",
            "options en": "options_en",
            "sdtm": "sdtm",
            "range min": "range_min",
            "range max": "range_max",
            "precision": "precision",
            "allowed missing value": "allowed_missing_values",
            "data sementic": "data_semantic",
            "data semantic": "data_semantic",
            "max length": "text_max_length",
            "min length": "text_min_length",
            "pattern validator": "pattern",
            "validators err mesage vi": "pattern_err_msg_vi",
            "validators err mesage en": "pattern_err_msg_en",
            "validators err message vi": "pattern_err_msg_vi",
            "validators err message en": "pattern_err_msg_en",
            "unit vi": "unit_vi",
            "unit en": "unit_en",
            "codelist vi": "codelist_vi",
            "codelist en": "codelist_en",
            "comments vi": "comments_vi",
            "comments en": "comments_en",
            "review study version": "review_study_version",
            "review type": "review_type",
            "review required for verify": "review_required_for_verify",
            "review required for lock": "review_required_for_lock",
            "review blocking if missing": "review_blocking_if_missing",
            "review role required": "review_role_required",
            "review enabled": "review_enabled",
        },
    }
    sheet_aliases = {
        template_fields_sheet_name: (
            template_fields_sheet_name,
            "Field Templates",
            "CRF Template Fields",
        ),
    }
    review_type_aliases = {
        "data_review": DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        "datareview": DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        "sdv": DataCaptureFieldReviewTypeChoices.SDV,
        "medical_review": DataCaptureFieldReviewTypeChoices.MEDICAL_REVIEW,
        "medical": DataCaptureFieldReviewTypeChoices.MEDICAL_REVIEW,
    }

    def __init__(self, crf_context_adapter=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()
        self._reset_template_ids_for_import = set()

    @staticmethod
    def _normalize_selected_study_id(selected_study_id):
        if selected_study_id is None:
            raise StudyScopeViolationError("No study is selected in the current context.")
        return int(selected_study_id)

    @classmethod
    def _ensure_current_study_scope(cls, *, selected_study_id, study_id):
        selected_study_id = cls._normalize_selected_study_id(selected_study_id)
        if int(study_id) != selected_study_id:
            raise StudyScopeViolationError("Command study scope does not match the selected study.")
        return selected_study_id

    def execute(self, command: ImportStudyCrfTemplateFieldsTemplateCommand) -> ImportStudyCrfTemplateFieldsTemplateResult:
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        workbook_rows_by_sheet = self._load_rows_from_workbook(
            file_name=command.file_name,
            file_content=command.file_content,
        )

        created_count = 0
        updated_count = 0
        issues = []
        rows = workbook_rows_by_sheet[self.template_fields_sheet_name]
        prepared_rows = []
        for row_number, row_data in rows:
            identifier = self._build_field_identifier(row_data)
            try:
                prepared_rows.append(
                    self._prepare_template_field_row(
                        study_id=command.study_id,
                        row_data=row_data,
                        row_number=row_number,
                        identifier=identifier,
                    )
                )
            except (CrfTemplateImportFormatError, FormBuilderDomainValidationError) as exc:
                issues.append(
                    CrfTemplateFieldImportIssue(
                        sheet_name=self.template_fields_sheet_name,
                        row_number=row_number,
                        identifier=identifier,
                        reason=str(exc),
                    )
                )

        import_now = self._now()
        for prepared_row in prepared_rows:
            try:
                crf_template_id = int(prepared_row.form_template.pk)
                if crf_template_id not in self._reset_template_ids_for_import:
                    self.crf_context_adapter.reset_import_template_fields(
                        crf_template_id=crf_template_id,
                        actor_user_id=command.actor_user_id,
                        now=import_now,
                    )
                    self._reset_template_ids_for_import.add(crf_template_id)

                import_outcome = self._import_prepared_template_field_row(
                    prepared_row=prepared_row,
                    actor_user_id=command.actor_user_id,
                    now=import_now,
                )
            except (CrfTemplateImportFormatError, FormBuilderDomainValidationError) as exc:
                issues.append(
                    CrfTemplateFieldImportIssue(
                        sheet_name=self.template_fields_sheet_name,
                        row_number=prepared_row.row_number,
                        identifier=prepared_row.identifier,
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        return ImportStudyCrfTemplateFieldsTemplateResult(
            total_rows=len(rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _prepare_template_field_row(self, *, study_id, row_data, row_number, identifier):
        form_name = self._require_text(
            row_data.get("form_name"),
            field_label="Form Name",
            max_length=255,
        )
        section_name = self._require_text(
            row_data.get("section_name"),
            field_label="Section Name",
            max_length=255,
        )
        form_template = self.crf_context_adapter.resolve_import_template_by_name_or_code(
            study_id=study_id,
            form_name=form_name,
        )
        section_template = self.crf_context_adapter.resolve_import_section_by_name_or_code(
            crf_template_id=form_template.pk,
            section_name=section_name,
        )
        payload = self._build_payload(row_data)
        return _PreparedTemplateFieldImportRow(
            row_number=row_number,
            identifier=identifier,
            form_template=form_template,
            section_template=section_template,
            payload=payload,
        )

    def _import_prepared_template_field_row(self, *, prepared_row, actor_user_id, now):
        import_outcome, field_template = self.crf_context_adapter.upsert_import_template_field(
            crf_template_id=prepared_row.form_template.pk,
            section_template_id=prepared_row.section_template.pk,
            payload=prepared_row.payload,
            actor_user_id=actor_user_id,
            now=now,
        )
        review_policy = prepared_row.payload.get("review_policy")
        if review_policy is not None:
            self.crf_context_adapter.upsert_import_field_review_policy(
                study_id=prepared_row.form_template.study_id,
                study_version=review_policy["study_version"],
                crf_template_id=prepared_row.form_template.pk,
                field_template_id=field_template.pk,
                review_type=review_policy["review_type"],
                is_required_for_page_verify=review_policy["is_required_for_page_verify"],
                is_required_for_lock=review_policy["is_required_for_lock"],
                is_blocking_if_missing=review_policy["is_blocking_if_missing"],
                role_required=review_policy["role_required"],
                is_enabled=review_policy["is_enabled"],
                actor_user_id=actor_user_id,
                now=now,
            )
        return import_outcome

    def _build_payload(self, row_data):
        range_min = self._coerce_optional_decimal(row_data.get("range_min"), field_label="Range Min")
        range_max = self._coerce_optional_decimal(row_data.get("range_max"), field_label="Range Max")
        if range_min is not None and range_max is not None and range_min > range_max:
            raise CrfTemplateImportFormatError("Range Min must be less than or equal to Range Max.")

        text_max_length = self._coerce_optional_non_negative_int(
            row_data.get("text_max_length"),
            field_label="Max Length",
        )
        text_min_length = self._coerce_optional_non_negative_int(
            row_data.get("text_min_length"),
            field_label="Min Length",
        )
        if text_max_length is not None and text_min_length is not None and text_min_length > text_max_length:
            raise CrfTemplateImportFormatError("Min Length must be less than or equal to Max Length.")

        return {
            "field_key": self._require_text(row_data.get("field_name"), field_label="Field Name", max_length=100),
            "label_vi": self._nullable_text(row_data.get("field_description_vi")),
            "label_en": self._nullable_text(row_data.get("field_description_en")),
            "data_type": self._require_text(row_data.get("data_type"), field_label="Data Type", max_length=20),
            "display_order": self._coerce_positive_int(row_data.get("display_order"), field_label="Display Order"),
            "control_type": self._require_text(row_data.get("control_type"), field_label="Control Type", max_length=50),
            "control_layout": self._nullable_text(row_data.get("control_layout")),
            "layout": self._nullable_text(row_data.get("layout")),
            "behavior": self._nullable_text(row_data.get("behavior")),
            "style": self._nullable_text(row_data.get("style")),
            "classes": self._nullable_text(row_data.get("classes")),
            "text_vi": self._nullable_text(row_data.get("text_vi")),
            "text_en": self._nullable_text(row_data.get("text_en")),
            "options_vi": self._nullable_text(row_data.get("options_vi")),
            "options_en": self._nullable_text(row_data.get("options_en")),
            "sdtm": self._nullable_text(row_data.get("sdtm")),
            "range_min": range_min,
            "range_max": range_max,
            "precision": self._coerce_optional_non_negative_int(row_data.get("precision"), field_label="Precision"),
            "allowed_missing_values": self._nullable_text(row_data.get("allowed_missing_values")),
            "data_semantic": self._nullable_text(row_data.get("data_semantic")),
            "text_max_length": text_max_length,
            "text_min_length": text_min_length,
            "pattern": self._nullable_text(row_data.get("pattern")),
            "pattern_err_msg_vi": self._nullable_text(row_data.get("pattern_err_msg_vi")),
            "pattern_err_msg_en": self._nullable_text(row_data.get("pattern_err_msg_en")),
            "unit_vi": self._nullable_text(row_data.get("unit_vi")),
            "unit_en": self._nullable_text(row_data.get("unit_en")),
            "codelist_vi": self._nullable_text(row_data.get("codelist_vi")),
            "codelist_en": self._nullable_text(row_data.get("codelist_en")),
            "comments_vi": self._nullable_text(row_data.get("comments_vi")),
            "comments_en": self._nullable_text(row_data.get("comments_en")),
            "review_policy": self._build_review_policy_payload(row_data),
        }

    def _build_review_policy_payload(self, row_data):
        if not self._has_review_policy_payload(row_data):
            return None
        return {
            "study_version": self._require_text(
                row_data.get("review_study_version"),
                field_label="Review Study Version",
                max_length=20,
            ),
            "review_type": self._normalize_review_type(row_data.get("review_type")),
            "is_required_for_page_verify": self._coerce_bool(
                row_data.get("review_required_for_verify"),
                field_label="Review Required For Verify",
                default=True,
            ),
            "is_required_for_lock": self._coerce_bool(
                row_data.get("review_required_for_lock"),
                field_label="Review Required For Lock",
                default=False,
            ),
            "is_blocking_if_missing": self._coerce_bool(
                row_data.get("review_blocking_if_missing"),
                field_label="Review Blocking If Missing",
                default=True,
            ),
            "role_required": self._nullable_text(row_data.get("review_role_required"), max_length=64),
            "is_enabled": self._coerce_bool(
                row_data.get("review_enabled"),
                field_label="Review Enabled",
                default=True,
            ),
        }

    def _has_review_policy_payload(self, row_data):
        review_keys = (
            "review_study_version",
            "review_type",
            "review_required_for_verify",
            "review_required_for_lock",
            "review_blocking_if_missing",
            "review_role_required",
            "review_enabled",
        )
        return any(self._as_text(row_data.get(key)) for key in review_keys)

    def _normalize_review_type(self, value):
        normalized = self._as_text(value).lower().replace("-", "_").replace(" ", "_")
        normalized = normalized or "data_review"
        review_type = self.review_type_aliases.get(normalized)
        if review_type is None:
            raise CrfTemplateImportFormatError(f"Invalid Review Type: {value!r}")
        return review_type

    def _nullable_text(self, value, *, max_length=None):
        normalized_value = self._as_text(value)
        if max_length is not None and len(normalized_value) > max_length:
            raise CrfTemplateImportFormatError(f"Value must be {max_length} characters or fewer.")
        return normalized_value or None

    def _coerce_optional_decimal(self, value, *, field_label):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return None
        try:
            return Decimal(normalized_value)
        except InvalidOperation as exc:
            raise CrfTemplateImportFormatError(f"{field_label} must be a decimal number.") from exc

    def _build_field_identifier(self, row_data):
        return " / ".join(
            part for part in (
                self._as_text(row_data.get("form_name")),
                self._as_text(row_data.get("section_name")),
                self._as_text(row_data.get("field_name")),
            ) if part
        )


__all__ = ["ImportStudyCrfTemplateFieldsTemplateService"]
