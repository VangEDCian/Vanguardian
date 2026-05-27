from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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
        },
    }
    sheet_aliases = {
        template_fields_sheet_name: (
            template_fields_sheet_name,
            "Field Templates",
            "CRF Template Fields",
        ),
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
        import_outcome, _field_template = self.crf_context_adapter.upsert_import_template_field(
            crf_template_id=prepared_row.form_template.pk,
            section_template_id=prepared_row.section_template.pk,
            payload=prepared_row.payload,
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
        }

    def _nullable_text(self, value):
        normalized_value = self._as_text(value)
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
