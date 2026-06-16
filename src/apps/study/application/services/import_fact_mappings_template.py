from io import BytesIO

from django.db import transaction
from django.utils import timezone

from apps.crf.domain.exceptions import StudyScopeViolationError
from apps.crf.public import (
    CrfContextAdapter,
    CrfTemplateAmbiguousError,
    CrfTemplateNotFoundError,
)
from apps.study.application.commands.import_fact_mappings_template import (
    FactMappingImportDependencyError,
    FactMappingImportFormatError,
    FactMappingImportIssue,
    ImportStudyFactMappingsTemplateCommand,
    ImportStudyFactMappingsTemplateResult,
)
from apps.study.infrastructure.repositories import DjangoStudyEventRepository


class ImportStudyFactMappingsTemplateService:
    crf_context_adapter_class = CrfContextAdapter
    repository_class = DjangoStudyEventRepository
    expected_columns = (
        "Event Code",
        "Form Code",
        "Field Code",
        "Source Path",
        "Fact Key",
        "Operator",
        "Expected Value",
        "Value Type",
        "Default Value",
        "Display Order",
    )
    expected_header_map = {
        "event code": "event_code",
        "form code": "form_code",
        "field code": "field_code",
        "source path": "source_path",
        "fact key": "fact_key",
        "operator": "operator",
        "expected value": "expected_value",
        "value type": "value_type",
        "default value": "default_value",
        "display order": "display_order",
    }
    operators = {
        "equals",
        "not_equals",
        "in",
        "not_in",
        "gt",
        "gte",
        "lt",
        "lte",
        "exists",
        "not_exists",
        "is_true",
        "is_false",
        "is_empty",
        "is_not_empty",
    }
    value_types = {"string", "boolean", "number", "decimal", "integer", "json"}

    def __init__(self, crf_context_adapter=None, datacapture_fact_mapping_config_adapter=None, repository=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()
        self.datacapture_fact_mapping_config_adapter = (
            datacapture_fact_mapping_config_adapter or self._build_datacapture_fact_mapping_config_adapter()
        )
        self.repository = repository or self.repository_class()

    @staticmethod
    def _build_datacapture_fact_mapping_config_adapter():
        from apps.datacapture.public import DataCaptureFactMappingConfigAdapter

        return DataCaptureFactMappingConfigAdapter()

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

    def execute(self, command: ImportStudyFactMappingsTemplateCommand) -> ImportStudyFactMappingsTemplateResult:
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        workbook_rows = self._load_rows_from_workbook(
            file_name=command.file_name,
            file_content=command.file_content,
        )

        created_count = 0
        updated_count = 0
        issues = []
        now = timezone.now()

        for row_number, row_data in workbook_rows:
            try:
                import_outcome = self._import_row(
                    study_id=command.study_id,
                    row_data=row_data,
                    actor_user_id=command.actor_user_id,
                    now=now,
                )
            except FactMappingImportFormatError as exc:
                issues.append(
                    FactMappingImportIssue(
                        row_number=row_number,
                        event_code=str(row_data.get("event_code", "") or ""),
                        form_code=str(row_data.get("form_code", "") or ""),
                        fact_key=str(row_data.get("fact_key", "") or ""),
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        return ImportStudyFactMappingsTemplateResult(
            total_rows=len(workbook_rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_row(self, *, study_id, row_data, actor_user_id, now):
        event_code = self._require_text(row_data.get("event_code"), field_label="Event Code")
        form_code = self._require_text(row_data.get("form_code"), field_label="Form Code")
        fact_key = self._require_text(row_data.get("fact_key"), field_label="Fact Key", max_length=128)
        field_code = self._nullable_text(row_data.get("field_code"), max_length=128)
        source_path = self._nullable_text(row_data.get("source_path"), max_length=512) or field_code
        if not source_path:
            raise FactMappingImportFormatError("Source Path is required when Field Code is blank.")

        event_definition = self._resolve_event_definition(study_id=study_id, event_code=event_code)
        form_definition = self._resolve_form_definition(study_id=study_id, form_code=form_code)
        operator = self._normalize_allowed_value(
            value=row_data.get("operator"),
            allowed_values=self.operators,
            field_label="Operator",
            default="equals",
        )
        value_type = self._normalize_allowed_value(
            value=row_data.get("value_type"),
            allowed_values=self.value_types,
            field_label="Value Type",
            default="string",
        )
        display_order = self._coerce_int(
            row_data.get("display_order"),
            field_label="Display Order",
            default=1,
        )
        if display_order < 1:
            raise FactMappingImportFormatError("Display Order must be greater than 0.")

        with transaction.atomic():
            result = self.datacapture_fact_mapping_config_adapter.upsert_fact_mapping(
                study_id=study_id,
                study_version=event_definition.study_version,
                event_definition_id=event_definition.pk,
                crf_template_id=form_definition.pk,
                field_code=field_code,
                source_path=source_path,
                fact_key=fact_key,
                operator=operator,
                expected_value=self._nullable_text(row_data.get("expected_value")),
                value_type=value_type,
                default_value=self._nullable_text(row_data.get("default_value")),
                display_order=display_order,
                actor_user_id=actor_user_id,
                now=now,
            )
        return result.outcome

    def _resolve_event_definition(self, *, study_id, event_code):
        event_definitions = list(
            self.repository.list_active_event_definitions_by_code(
                study_id=study_id,
                code=event_code,
            )
        )
        count = len(event_definitions)
        if count == 0:
            raise FactMappingImportFormatError("Event Code was not found.")
        if count > 1:
            raise FactMappingImportFormatError(
                "Event Code matched multiple event definitions. Please make the code unique across study versions."
            )
        return event_definitions[0]

    def _resolve_form_definition(self, *, study_id, form_code):
        try:
            return self.crf_context_adapter.resolve_unique_template_by_code(
                study_id=study_id,
                code=form_code,
                case_insensitive=True,
            )
        except CrfTemplateNotFoundError as exc:
            raise FactMappingImportFormatError("Form Code was not found.") from exc
        except CrfTemplateAmbiguousError as exc:
            raise FactMappingImportFormatError(
                "Form Code matched multiple CRF templates. Please make the code unique across template versions."
            ) from exc

    def _load_rows_from_workbook(self, *, file_name, file_content):
        file_name_lower = (file_name or "").strip().lower()
        if file_name_lower.endswith(".xlsx"):
            return self._load_xlsx_rows(file_content)
        if file_name_lower.endswith(".xls"):
            return self._load_xls_rows(file_content)
        raise FactMappingImportFormatError("Only .xlsx and .xls files are supported.")

    def _load_xlsx_rows(self, file_content):
        try:
            from openpyxl import load_workbook
        except ModuleNotFoundError as exc:
            raise FactMappingImportDependencyError(
                "Excel import support for .xlsx is not installed. Install openpyxl first."
            ) from exc

        workbook = load_workbook(filename=BytesIO(file_content), data_only=True, read_only=True)
        worksheet = workbook.worksheets[0]
        rows = list(worksheet.iter_rows(values_only=True))
        return self._map_rows(rows)

    def _load_xls_rows(self, file_content):
        try:
            import xlrd
        except ModuleNotFoundError as exc:
            raise FactMappingImportDependencyError(
                "Excel import support for .xls is not installed. Install xlrd first."
            ) from exc

        workbook = xlrd.open_workbook(file_contents=file_content)
        worksheet = workbook.sheet_by_index(0)
        rows = [worksheet.row_values(index) for index in range(worksheet.nrows)]
        return self._map_rows(rows)

    def _map_rows(self, rows):
        if not rows:
            raise FactMappingImportFormatError("The workbook is empty.")

        headers = [self._normalize_header(value) for value in rows[0]]
        missing_headers = [
            header
            for header in self.expected_columns
            if self._normalize_header(header) not in headers
        ]
        if missing_headers:
            raise FactMappingImportFormatError(
                "Missing required columns: " + ", ".join(missing_headers)
            )

        header_keys = [self.expected_header_map.get(header) for header in headers]
        mapped_rows = []
        for row_index, row_values in enumerate(rows[1:], start=2):
            if self._is_blank_row(row_values):
                continue

            row_data = {}
            for column_index, header_key in enumerate(header_keys):
                if not header_key:
                    continue
                row_data[header_key] = row_values[column_index] if column_index < len(row_values) else None

            mapped_rows.append((row_index, row_data))

        return mapped_rows

    @staticmethod
    def _normalize_header(value):
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _is_blank_row(row_values):
        return all(str(value or "").strip() == "" for value in row_values)

    @staticmethod
    def _as_text(value):
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    def _require_text(self, value, *, field_label, max_length=None):
        normalized_value = self._as_text(value)
        if not normalized_value:
            raise FactMappingImportFormatError(f"{field_label} is required.")
        if max_length is not None and len(normalized_value) > max_length:
            raise FactMappingImportFormatError(f"{field_label} must be at most {max_length} characters.")
        return normalized_value

    def _nullable_text(self, value, *, max_length=None):
        normalized_value = self._as_text(value)
        if not normalized_value:
            return None
        if max_length is not None and len(normalized_value) > max_length:
            raise FactMappingImportFormatError(f"Value must be at most {max_length} characters.")
        return normalized_value

    def _normalize_allowed_value(self, *, value, allowed_values, field_label, default):
        normalized_value = self._as_text(value).lower().replace("-", "_").replace(" ", "_")
        normalized_value = normalized_value or default
        if normalized_value not in allowed_values:
            raise FactMappingImportFormatError(f"Invalid {field_label}: {value!r}")
        return normalized_value

    def _coerce_int(self, value, *, field_label, default=None):
        normalized = self._as_text(value)
        if not normalized:
            if default is not None:
                return default
            raise FactMappingImportFormatError(f"{field_label} is required.")

        try:
            return int(float(normalized))
        except ValueError as exc:
            raise FactMappingImportFormatError(f"{field_label} must be a number.") from exc


__all__ = ["ImportStudyFactMappingsTemplateService"]
