import abc
from abc import abstractmethod
from dataclasses import replace

from django.core.exceptions import ValidationError

from apps.study.application.use_cases.randomization_import_preview import RandomizationImportIssue
from apps.study.domain import RandomizationScheme


class BaseRandomizationImportValidationService(abc.ABC):
    model_validation_exclude_fields: tuple[str, ...] = ()

    @staticmethod
    def _resolve_scheme_status(*, values, existing_scheme=None):
        imported_status = BaseRandomizationImportValidationService._optional_value(values, "status")
        if imported_status is not None:
            return imported_status
        if existing_scheme is not None:
            return getattr(existing_scheme, "status", RandomizationScheme.DRAFT)
        return RandomizationScheme.DRAFT

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
