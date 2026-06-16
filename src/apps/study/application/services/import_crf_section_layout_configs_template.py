import json

from apps.crf.domain.exceptions import FormBuilderDomainValidationError, StudyScopeViolationError
from apps.crf.public import CrfContextAdapter
from apps.study.application.commands.import_crf_section_layout_configs_template import (
    CrfSectionLayoutConfigImportIssue,
    ImportStudyCrfSectionLayoutConfigsTemplateCommand,
    ImportStudyCrfSectionLayoutConfigsTemplateResult,
)
from apps.study.application.commands.import_crf_templates_template import CrfTemplateImportFormatError
from apps.study.application.commands.import_crf_templates_template.workbook import CrfTemplateWorkbookMixin


class ImportStudyCrfSectionLayoutConfigsTemplateService(CrfTemplateWorkbookMixin):
    crf_context_adapter_class = CrfContextAdapter
    section_layout_configs_sheet_name = "Section Layout Configs"
    expected_columns = {
        section_layout_configs_sheet_name: (
            "Form Name",
            "Section Name",
            "Layout Type",
            "Column Count",
            "Label Position",
            "Density",
            "Section Style",
            "Is Collapsible",
            "Is Expanded By Default",
            "Show Section Header",
            "Show Border",
            "Show Background",
            "Custom CSS Class",
            "Custom Layout Schema",
        ),
    }
    expected_header_map = {
        section_layout_configs_sheet_name: {
            "form name": "form_name",
            "section name": "section_name",
            "layout type": "layout_type",
            "column count": "column_count",
            "label position": "label_position",
            "density": "density",
            "section style": "section_style",
            "is collapsible": "is_collapsible",
            "is expanded by default": "is_expanded_by_default",
            "show section header": "show_section_header",
            "show border": "show_border",
            "show background": "show_background",
            "custom css class": "custom_css_class",
            "custom layout schema": "custom_layout_schema",
        },
    }
    sheet_aliases = {
        section_layout_configs_sheet_name: (
            section_layout_configs_sheet_name,
            "Section Layout Config",
            "crf_section_layoutconfig",
        ),
    }

    def __init__(self, crf_context_adapter=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()

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

    def execute(
        self,
        command: ImportStudyCrfSectionLayoutConfigsTemplateCommand,
    ) -> ImportStudyCrfSectionLayoutConfigsTemplateResult:
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
        rows = workbook_rows_by_sheet[self.section_layout_configs_sheet_name]
        for row_number, row_data in rows:
            identifier = self._build_section_identifier(row_data)
            try:
                import_outcome = self._import_section_layout_config_row(
                    selected_study_id=command.selected_study_id,
                    study_id=command.study_id,
                    row_data=row_data,
                    actor_user_id=command.actor_user_id,
                )
            except (CrfTemplateImportFormatError, FormBuilderDomainValidationError) as exc:
                issues.append(
                    CrfSectionLayoutConfigImportIssue(
                        sheet_name=self.section_layout_configs_sheet_name,
                        row_number=row_number,
                        identifier=identifier,
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        return ImportStudyCrfSectionLayoutConfigsTemplateResult(
            total_rows=len(rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_section_layout_config_row(self, *, selected_study_id, study_id, row_data, actor_user_id):
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
        return self.crf_context_adapter.upsert_section_layout_config(
            selected_study_id=selected_study_id,
            section_template_id=section_template.pk,
            layout_type=self._optional_text(row_data.get("layout_type"), default="section", max_length=32),
            column_count=self._optional_positive_int(row_data.get("column_count"), default=1, field_label="Column Count"),
            label_position=self._optional_text(row_data.get("label_position"), default="top", max_length=16),
            density=self._optional_text(row_data.get("density"), default="standard", max_length=16),
            section_style=self._optional_text(row_data.get("section_style"), default="plain", max_length=32),
            is_collapsible=self._coerce_bool_with_default(
                row_data.get("is_collapsible"),
                default=False,
                field_label="Is Collapsible",
            ),
            is_expanded_by_default=self._coerce_bool_with_default(
                row_data.get("is_expanded_by_default"),
                default=True,
                field_label="Is Expanded By Default",
            ),
            show_section_header=self._coerce_bool_with_default(
                row_data.get("show_section_header"),
                default=True,
                field_label="Show Section Header",
            ),
            show_border=self._coerce_bool_with_default(
                row_data.get("show_border"),
                default=False,
                field_label="Show Border",
            ),
            show_background=self._coerce_bool_with_default(
                row_data.get("show_background"),
                default=False,
                field_label="Show Background",
            ),
            custom_css_class=self._nullable_text(row_data.get("custom_css_class"), max_length=128),
            custom_layout_schema=self._nullable_json(row_data.get("custom_layout_schema")),
            actor_user_id=actor_user_id,
            now=self._now(),
        )

    def _build_section_identifier(self, row_data):
        form_name = self._as_text(row_data.get("form_name")) or "Unknown Form"
        section_name = self._as_text(row_data.get("section_name")) or "Unknown Section"
        return f"{form_name} / {section_name}"

    def _nullable_text(self, value, *, max_length=None):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return None
        if max_length is not None and len(normalized_value) > max_length:
            raise CrfTemplateImportFormatError(f"Value must be at most {max_length} characters.")
        return normalized_value

    def _optional_text(self, value, *, default, max_length):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return default
        if len(normalized_value) > max_length:
            raise CrfTemplateImportFormatError(f"Value must be at most {max_length} characters.")
        return normalized_value

    def _optional_positive_int(self, value, *, default, field_label):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return default
        return self._coerce_positive_int(normalized_value, field_label=field_label)

    def _coerce_bool_with_default(self, value, *, default, field_label):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return default
        return self._coerce_bool(normalized_value, field_label=field_label)

    def _nullable_json(self, value):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return None
        try:
            parsed_value = json.loads(normalized_value)
        except json.JSONDecodeError as exc:
            raise CrfTemplateImportFormatError("Custom Layout Schema must be valid JSON.") from exc
        if not isinstance(parsed_value, dict):
            raise CrfTemplateImportFormatError("Custom Layout Schema must be a JSON object.")
        return parsed_value


__all__ = ["ImportStudyCrfSectionLayoutConfigsTemplateService"]
