from django.utils.translation import gettext_lazy as _

from apps.study.application.use_cases.randomization_import_preview.base import BaseRandomizationImportPreviewUseCase
from apps.study.application.use_cases.randomization_import_preview.types import (
    RandomizationImportColumn,
    RandomizationImportFormatError,
)


class RandomizationSequencePeriodImportPreviewUseCase(BaseRandomizationImportPreviewUseCase):
    columns = (
        RandomizationImportColumn(
            "scheme_code",
            "Scheme Code",
            max_length=64,
            aliases=("Scheme",),
        ),
        RandomizationImportColumn(
            "arm_code",
            "Arm Code",
            max_length=32,
            aliases=("Arm",),
        ),
        RandomizationImportColumn(
            "period_no",
            "Period No",
            data_type="integer",
            aliases=("Period",),
        ),
        RandomizationImportColumn(
            "treatment_code",
            "Treatment Code",
            max_length=64,
            aliases=("Treatment",),
        ),
        RandomizationImportColumn(
            "start_event_code",
            "Start Event Code",
            max_length=255,
            aliases=("Start Event",),
        ),
        RandomizationImportColumn(
            "end_event_code",
            "End Event Code",
            max_length=255,
            aliases=("End Event",),
        ),
        RandomizationImportColumn(
            "washout_days",
            "Washout Days",
            data_type="integer",
            required=False,
            aliases=("Washout",),
        ),
        RandomizationImportColumn(
            "transition_rule_code",
            "Transition Rule Code",
            required=False,
            max_length=64,
            aliases=("Transition Rule",),
        ),
        RandomizationImportColumn(
            "display_order",
            "Display Order",
            data_type="integer",
            aliases=("Order",),
        ),
    )

    def _coerce_value(self, *, raw_value, column):
        if column.key in {"washout_days", "transition_rule_code"} and self._is_null_text(raw_value):
            return ""
        return super()._coerce_value(raw_value=raw_value, column=column)

    def _coerce_int(self, value, *, field_label):
        parsed_value = super()._coerce_int(value, field_label=field_label)
        if parsed_value < 0:
            raise RandomizationImportFormatError(
                str(_("%(column)s must be zero or greater.") % {"column": field_label})
            )
        return parsed_value

    @staticmethod
    def split_event_code_candidates(value):
        return tuple(
            candidate.strip()
            for candidate in str(value or "").replace("|", "/").split("/")
            if candidate.strip()
        )

    @staticmethod
    def _is_null_text(value):
        return str(value or "").strip().lower() in {"null", "none", "n/a", "na"}

    def _build_identifier(self, cleaned_values, row_data):
        scheme_code = cleaned_values.get("scheme_code") or self._as_text(row_data.get("scheme_code"))
        arm_code = cleaned_values.get("arm_code") or self._as_text(row_data.get("arm_code"))
        period_no = cleaned_values.get("period_no") or self._as_text(row_data.get("period_no"))
        return " / ".join(
            part
            for part in (
                str(scheme_code).strip(),
                str(arm_code).strip(),
                str(period_no).strip(),
            )
            if part
        )

    def _build_identifier_from_row_data(self, row_data):
        return " / ".join(
            part
            for part in (
                self._as_text(row_data.get("scheme_code")),
                self._as_text(row_data.get("arm_code")),
                self._as_text(row_data.get("period_no")),
            )
            if part
        ) or str(_("(no code)"))

    def _build_duplicate_key(self, cleaned_values):
        return (
            str(cleaned_values.get("scheme_code", "")).lower(),
            str(cleaned_values.get("arm_code", "")).lower(),
            cleaned_values.get("period_no"),
        )

    def _get_duplicate_column_label(self):
        return "Scheme Code / Arm Code / Period No"
