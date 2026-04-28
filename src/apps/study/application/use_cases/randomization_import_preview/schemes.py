from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.choices.study import RandomizationSchemeStatusChoice
from apps.study.application.use_cases.randomization_import_preview.base import BaseRandomizationImportPreviewUseCase
from apps.study.application.use_cases.randomization_import_preview.types import (
    RandomizationImportColumn,
    RandomizationImportFormatError,
)


class RandomizationSchemeImportPreviewUseCase(BaseRandomizationImportPreviewUseCase):
    allowed_status_values = {choice.value for choice in RandomizationSchemeStatusChoice}

    columns = (
        RandomizationImportColumn("code", "Code", max_length=64),
        RandomizationImportColumn("name", "Name", max_length=255),
        RandomizationImportColumn(
            "randomization_type",
            "Type",
            max_length=32,
            aliases=("Randomization Type",),
        ),
        RandomizationImportColumn(
            "allocation_ratio_json",
            "Allocation Ratio",
            required=False,
            aliases=("Allocation",),
        ),
        RandomizationImportColumn(
            "target_randomized_total",
            "Target Randomized Total",
            data_type="integer",
            aliases=("Target Total",),
        ),
        RandomizationImportColumn(
            "is_open_label",
            "Is Open Label",
            data_type="boolean",
            aliases=("Open Label",),
        ),
        RandomizationImportColumn(
            "requires_screening_pass",
            "Requires Screening Pass",
            data_type="boolean",
            aliases=("Requires Screening",),
        ),
        RandomizationImportColumn(
            "eligibility_rule_code",
            "Eligibility Rule Code",
            required=False,
            max_length=64,
            aliases=("Eligibility Rule",),
        ),
        RandomizationImportColumn(
            "effective_from",
            "Effective From",
            required=False,
        ),
        RandomizationImportColumn(
            "effective_to",
            "Effective To",
            required=False,
        ),
        RandomizationImportColumn(
            "status",
            "Status",
            required=False,
            max_length=32,
            aliases=("Scheme Status", "Randomization Status"),
        ),
        RandomizationImportColumn(
            "notes",
            "Notes",
            required=False,
        ),
    )

    def _coerce_value(self, *, raw_value, column):
        if column.key == "allocation_ratio_json":
            return self._coerce_allocation_ratio(raw_value, field_label=column.label)
        if column.key in {"effective_from", "effective_to"}:
            return self._coerce_datetime(raw_value, field_label=column.label)
        if column.key == "status":
            return self._coerce_status(raw_value, field_label=column.label)
        return super()._coerce_value(raw_value=raw_value, column=column)

    def _coerce_allocation_ratio(self, value, *, field_label):
        if self._is_empty_value(value):
            return ""

        ratio_mapping = self._parse_allocation_ratio(value, field_label=field_label)
        normalized_mapping = {}
        for arm_code, ratio in ratio_mapping.items():
            normalized_code = self._as_text(arm_code)
            if not normalized_code:
                raise RandomizationImportFormatError(
                    str(_("%(column)s contains an empty ARM code.") % {"column": field_label})
                )
            normalized_mapping[normalized_code] = self._coerce_int(
                ratio,
                field_label=field_label,
            )

        for arm_code, ratio in normalized_mapping.items():
            if ratio <= 0:
                raise RandomizationImportFormatError(
                    str(
                        _("%(column)s ratio for %(arm_code)s must be greater than 0.")
                        % {"column": field_label, "arm_code": arm_code}
                    )
                )

        if not normalized_mapping:
            raise RandomizationImportFormatError(
                str(_("%(column)s must contain at least one ARM ratio.") % {"column": field_label})
            )

        return normalized_mapping

    def _parse_allocation_ratio(self, value, *, field_label) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        text_value = self._as_text(value)
        if text_value.startswith("{"):
            try:
                parsed = json.loads(text_value)
            except json.JSONDecodeError as exc:
                raise RandomizationImportFormatError(
                    str(
                        _(
                            "%(column)s must be valid JSON object or shorthand like ARM-A:2;ARM-B:1.",
                        )
                        % {"column": field_label}
                    )
                ) from exc
            if not isinstance(parsed, dict):
                raise RandomizationImportFormatError(
                    str(_("%(column)s must be a JSON object.") % {"column": field_label})
                )
            return parsed

        pairs = [segment.strip() for segment in text_value.replace(",", ";").split(";") if segment.strip()]
        mapping: dict[str, Any] = {}
        for pair in pairs:
            if ":" not in pair:
                raise RandomizationImportFormatError(
                    str(
                        _(
                            "%(column)s must be valid JSON object or shorthand like ARM-A:2;ARM-B:1.",
                        )
                        % {"column": field_label}
                    )
                )
            arm_code, ratio = pair.split(":", 1)
            mapping[self._as_text(arm_code)] = self._as_text(ratio)
        return mapping

    def _coerce_datetime(self, value, *, field_label):
        if self._is_empty_value(value):
            return ""

        if isinstance(value, datetime):
            return self._ensure_aware_datetime(value)
        if isinstance(value, date):
            return self._ensure_aware_datetime(
                datetime.combine(value, datetime.min.time()),
            )

        text_value = self._as_text(value).replace("T", " ")
        try:
            return self._ensure_aware_datetime(datetime.fromisoformat(text_value))
        except ValueError as exc:
            raise RandomizationImportFormatError(
                str(
                    _("%(column)s must be a valid datetime. Example: 2026-04-21 08:30")
                    % {"column": field_label}
                )
            ) from exc

    @staticmethod
    def _ensure_aware_datetime(value):
        if not settings.USE_TZ or timezone.is_aware(value):
            return value
        return timezone.make_aware(value, timezone.get_current_timezone())

    def _coerce_status(self, value, *, field_label):
        if self._is_empty_value(value):
            return ""

        normalized_value = self._as_text(value).lower()
        if normalized_value in self.allowed_status_values:
            return normalized_value
        raise RandomizationImportFormatError(
            str(
                _("%(column)s must be one of: %(choices)s")
                % {
                    "column": field_label,
                    "choices": ", ".join(sorted(self.allowed_status_values)),
                }
            )
        )

    def _build_identifier(self, cleaned_values, row_data):
        return str(cleaned_values.get("code") or self._build_identifier_from_row_data(row_data))

    def _build_identifier_from_row_data(self, row_data):
        return self._as_text(row_data.get("code")) or str(_("(no code)"))

    def _build_duplicate_key(self, cleaned_values):
        return (str(cleaned_values.get("code", "")).lower(),)

    def _get_duplicate_column_label(self):
        return "Code"
