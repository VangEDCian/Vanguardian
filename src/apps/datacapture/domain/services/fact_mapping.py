import json
from decimal import Decimal, InvalidOperation
from typing import Any

from jsonpath_ng.ext import parse as parse_jsonpath

from apps.datacapture.domain.entities import DataCaptureFactMappingRule, DataCaptureFactSource


class DataCaptureFactMappingEvaluator:
    MISSING = object()

    def build_facts(
        self,
        *,
        mappings: list[DataCaptureFactMappingRule],
        final_data: str | dict | list | None = None,
        fact_source: DataCaptureFactSource | None = None,
    ) -> dict[str, bool] | None:
        if not mappings:
            return None

        parsed_final_data, current_form_data = self._resolve_source_context(
            final_data=final_data,
            fact_source=fact_source,
        )
        if parsed_final_data is self.MISSING:
            return None

        facts: dict[str, bool] = {}
        for mapping in mappings:
            raw_value = self._resolve_value(parsed_final_data, mapping, current_form_data=current_form_data)
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

    def _resolve_value(
        self,
        final_data: Any,
        mapping: DataCaptureFactMappingRule,
        *,
        current_form_data: dict[str, Any] | None = None,
    ):
        source_path = (mapping.source_path or mapping.field_code or "").strip()
        if not source_path:
            return self.MISSING
        canonical_data = current_form_data if current_form_data is not None else final_data
        if isinstance(canonical_data, dict) and dict.get(canonical_data, "format") == "edc.form_data.v1":
            canonical_value = self._resolve_canonical_field_value(canonical_data, source_path)
            if canonical_value is not self.MISSING:
                return canonical_value

        jsonpath = self._normalize_source_path_to_jsonpath(source_path=source_path, final_data=final_data)
        return self._resolve_jsonpath_value(final_data=final_data, jsonpath=jsonpath)

    def _resolve_source_context(
        self,
        *,
        final_data: str | dict | list | None,
        fact_source: DataCaptureFactSource | None,
    ):
        if fact_source is not None:
            return fact_source.to_jsonpath_context(), fact_source.current_form_data()
        parsed_final_data = self._parse_final_data(final_data)
        return parsed_final_data, parsed_final_data if isinstance(parsed_final_data, dict) else None

    def _resolve_jsonpath_value(self, *, final_data: Any, jsonpath: str):
        try:
            matches = parse_jsonpath(jsonpath).find(final_data)
        except Exception:
            return self.MISSING
        if not matches:
            return self.MISSING
        if len(matches) == 1:
            return matches[0].value
        return [match.value for match in matches]

    @classmethod
    def _normalize_source_path_to_jsonpath(cls, *, source_path: str, final_data: Any) -> str:
        if source_path.startswith("$"):
            return source_path
        if isinstance(final_data, dict) and source_path in final_data:
            return "$" + cls._jsonpath_key(source_path)
        return "$." + source_path

    @staticmethod
    def _jsonpath_key(key: str) -> str:
        return "[" + json.dumps(str(key), ensure_ascii=True) + "]"

    def _resolve_canonical_field_value(self, final_data: dict, source_path: str):
        if source_path.startswith("groups."):
            return self.MISSING
        groups = dict.get(final_data, "groups")
        if not isinstance(groups, dict):
            return self.MISSING
        for group in groups.values():
            if not isinstance(group, dict):
                continue
            if group.get("kind") == "repeatable":
                rows = group.get("rows") if isinstance(group.get("rows"), list) else []
                for row in rows:
                    items = row.get("items") if isinstance(row, dict) and isinstance(row.get("items"), dict) else {}
                    if source_path in items:
                        return items[source_path]
                continue
            items = group.get("items") if isinstance(group.get("items"), dict) else {}
            if source_path in items:
                return items[source_path]
        return self.MISSING

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
