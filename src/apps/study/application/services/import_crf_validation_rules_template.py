from apps.crf.domain.exceptions import FormBuilderDomainValidationError, StudyScopeViolationError
from apps.crf.public import CrfContextAdapter
from apps.study.application.commands.import_crf_templates_template import CrfTemplateImportFormatError
from apps.study.application.commands.import_crf_templates_template.workbook import CrfTemplateWorkbookMixin
from apps.study.application.commands.import_crf_validation_rules_template import (
    CrfValidationRuleImportIssue,
    ImportStudyCrfValidationRulesTemplateCommand,
    ImportStudyCrfValidationRulesTemplateResult,
)


class ImportStudyCrfValidationRulesTemplateService(CrfTemplateWorkbookMixin):
    crf_context_adapter_class = CrfContextAdapter
    validation_rules_sheet_name = "Validation Rules"
    expected_columns = {
        validation_rules_sheet_name: (
            "Form Code",
            "Field Name",
            "Rule Type",
            "Expression",
            "Severity",
            "Mode",
            "Vi Message",
            "En Message",
        ),
    }
    expected_header_map = {
        validation_rules_sheet_name: {
            "form code": "form_code",
            "field name": "field_name",
            "rule type": "rule_type",
            "expression": "expression",
            "severity": "severity",
            "mode": "mode",
            "vi message": "vi_message",
            "en message": "en_message",
        },
    }
    sheet_aliases = {
        validation_rules_sheet_name: (
            validation_rules_sheet_name,
            "CRF Validation Rules",
            "crf_fieldvalidationrule",
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
        command: ImportStudyCrfValidationRulesTemplateCommand,
    ) -> ImportStudyCrfValidationRulesTemplateResult:
        selected_study_id = self._ensure_current_study_scope(
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
        rows = workbook_rows_by_sheet[self.validation_rules_sheet_name]
        for row_number, row_data in rows:
            identifier = self._build_validation_rule_identifier(row_data)
            try:
                import_outcome = self._import_validation_rule_row(
                    selected_study_id=selected_study_id,
                    row_data=row_data,
                    actor_user_id=command.actor_user_id,
                )
            except (CrfTemplateImportFormatError, FormBuilderDomainValidationError) as exc:
                issues.append(
                    CrfValidationRuleImportIssue(
                        sheet_name=self.validation_rules_sheet_name,
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

        return ImportStudyCrfValidationRulesTemplateResult(
            total_rows=len(rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_validation_rule_row(self, *, selected_study_id, row_data, actor_user_id):
        study_id = int(selected_study_id)

        form_code = self._require_text(row_data.get("form_code"), field_label="Form Code", max_length=64)
        field_name = self._require_text(row_data.get("field_name"), field_label="Field Name", max_length=100)
        form_template = self.crf_context_adapter.resolve_import_validation_rule_template_by_code(
            study_id=study_id,
            form_code=form_code,
        )
        field_template = self.crf_context_adapter.resolve_import_validation_rule_field_by_key(
            crf_template_id=form_template.pk,
            field_name=field_name,
        )
        rule_type = self._require_text(row_data.get("rule_type"), field_label="Rule Type", max_length=64)
        expression = self._expression_for_rule_type(
            rule_type=rule_type,
            raw_expression=row_data.get("expression"),
        )
        import_outcome, _validation_rule = self.crf_context_adapter.upsert_import_validation_rule(
            study_id=study_id,
            crf_template_id=form_template.pk,
            field_template_id=field_template.pk,
            rule_type=rule_type,
            expression=expression,
            severity=self._require_text(row_data.get("severity"), field_label="Severity", max_length=20),
            mode=self._require_text(row_data.get("mode"), field_label="Mode", max_length=20),
            vi_message=self._require_text(row_data.get("vi_message"), field_label="Vi Message", max_length=10000),
            en_message=self._require_text(row_data.get("en_message"), field_label="En Message", max_length=10000),
            actor_user_id=actor_user_id,
            now=self._now(),
        )
        return import_outcome

    def _expression_for_rule_type(self, *, rule_type, raw_expression):
        normalized_rule_type = str(rule_type or "").strip().upper()
        if normalized_rule_type == "REQUIRED":
            return self._as_text(raw_expression)[:10000]
        return self._require_text(raw_expression, field_label="Expression", max_length=10000)

    def _build_validation_rule_identifier(self, row_data):
        return " / ".join(
            part for part in (
                self._as_text(row_data.get("form_code")),
                self._as_text(row_data.get("field_name")),
                self._as_text(row_data.get("rule_type")),
            ) if part
        )


__all__ = ["ImportStudyCrfValidationRulesTemplateService"]
