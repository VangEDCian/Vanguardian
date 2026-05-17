import json
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.datacapture.domain.entities import DataCaptureFactMappingRule


class DataCaptureFactMappingEvaluator:
    MISSING = object()

    def build_facts(
        self,
        *,
        final_data: str | dict | list | None,
        mappings: list[DataCaptureFactMappingRule],
    ) -> dict[str, bool] | None:
        if not mappings:
            return None

        parsed_final_data = self._parse_final_data(final_data)
        if parsed_final_data is self.MISSING:
            return None

        facts: dict[str, bool] = {}
        for mapping in mappings:
            raw_value = self._resolve_value(parsed_final_data, mapping)
            facts[mapping.fact_key] = self._evaluate_mapping(raw_value, mapping)

        return facts or None

    def _evaluate_mapping(
        self,
        raw_value: Any,
        mapping: DataCaptureFactMappingRule,
    ) -> bool:
        operator = (mapping.operator or "equals").strip().lower()
        expected_value = self._coerce_expected_value(mapping)

        if raw_value is self.MISSING:
            raw_value = self._coerce_value(mapping.default_value, mapping.value_type)
            if raw_value is self.MISSING:
                return operator in {"not_exists", "is_empty"}

        value = self._coerce_value(raw_value, mapping.value_type)
        operator_handlers = {
            "exists": lambda: value is not self.MISSING,
            "not_exists": lambda: value is self.MISSING,
            "equals": lambda: value == expected_value,
            "not_equals": lambda: value != expected_value,
            "in": lambda: value in self._coerce_expected_collection(mapping),
            "not_in": lambda: value not in self._coerce_expected_collection(mapping),
            "gt": lambda: self._compare(value, expected_value, lambda left, right: left > right),
            "gte": lambda: self._compare(value, expected_value, lambda left, right: left >= right),
            "lt": lambda: self._compare(value, expected_value, lambda left, right: left < right),
            "lte": lambda: self._compare(value, expected_value, lambda left, right: left <= right),
            "is_true": lambda: value is True,
            "is_false": lambda: value is False,
            "is_empty": lambda: value in (None, "", [], {}),
            "is_not_empty": lambda: value not in (None, "", [], {}),
        }

        return operator_handlers.get(operator, lambda: False)()

    def _resolve_value(self, final_data: Any, mapping: DataCaptureFactMappingRule):
        source_path = (mapping.source_path or mapping.field_code or "").strip()
        if not source_path:
            return self.MISSING

        current_value = final_data
        for segment in source_path.split("."):
            if segment == "":
                continue
            if isinstance(current_value, dict):
                if segment not in current_value:
                    return self.MISSING
                current_value = current_value[segment]
                continue
            if isinstance(current_value, list):
                try:
                    current_value = current_value[int(segment)]
                except (IndexError, TypeError, ValueError):
                    return self.MISSING
                continue
            return self.MISSING

        return current_value

    def _coerce_expected_value(self, mapping: DataCaptureFactMappingRule):
        return self._coerce_value(mapping.expected_value, mapping.value_type)

    def _coerce_expected_collection(self, mapping: DataCaptureFactMappingRule) -> list:
        expected_value = mapping.expected_value
        if expected_value in (None, ""):
            return []
        if isinstance(expected_value, list):
            raw_values = expected_value
        else:
            try:
                decoded_value = json.loads(expected_value)
            except (TypeError, json.JSONDecodeError):
                decoded_value = None
            raw_values = decoded_value if isinstance(decoded_value, list) else str(expected_value).split(",")
        return [self._coerce_value(value, mapping.value_type) for value in raw_values]

    def _coerce_value(self, value: Any, value_type: str):
        if value is self.MISSING:
            return self.MISSING
        if value is None:
            return None

        normalized_type = (value_type or "string").strip().lower()
        if normalized_type == "boolean":
            return self._coerce_bool(value)
        if normalized_type in {"number", "decimal"}:
            return self._coerce_decimal(value)
        if normalized_type == "integer":
            decimal_value = self._coerce_decimal(value)
            return int(decimal_value) if decimal_value is not self.MISSING else self.MISSING
        if normalized_type == "json" and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return self.MISSING
        return str(value).strip() if isinstance(value, str) else value

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        normalized_value = str(value).strip().lower()
        return normalized_value in {"1", "true", "yes", "y", "on", "pass", "passed"}

    def _coerce_decimal(self, value: Any):
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return self.MISSING

    def _parse_final_data(self, final_data: str | dict | list | None):
        if isinstance(final_data, (dict, list)):
            return final_data
        if final_data in (None, ""):
            return self.MISSING
        try:
            return json.loads(final_data)
        except (TypeError, json.JSONDecodeError):
            return self.MISSING

    @staticmethod
    def _compare(value, expected_value, comparator) -> bool:
        if value in (None, DataCaptureFactMappingEvaluator.MISSING):
            return False
        if expected_value in (None, DataCaptureFactMappingEvaluator.MISSING):
            return False
        return comparator(value, expected_value)


__all__ = ["DataCaptureFactMappingEvaluator"]
