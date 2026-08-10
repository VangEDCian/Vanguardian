import json
from collections import defaultdict
from typing import Any

from apps.core.form_data_document import iter_field_values, normalize_form_data
from apps.datacapture.infrastructure.repositories.subject_export import (
    DjangoSubjectExportDataRepository,
)


class SubjectExportDataService:
    repository_class = DjangoSubjectExportDataRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def read_values(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        field_specs: tuple[dict, ...],
    ) -> dict[int, tuple[dict[str, Any], ...]]:
        if not subject_ids or not field_specs:
            return {}

        specs_by_binding_id: dict[int, list[dict]] = defaultdict(list)
        specs_by_event_form: dict[tuple[int, int], list[dict]] = defaultdict(list)
        for spec in field_specs:
            specs_by_binding_id[int(spec["binding_id"])].append(spec)
            specs_by_event_form[
                (
                    int(spec["event_definition_id"]),
                    int(spec["crf_template_id"]),
                )
            ].append(spec)

        base_values: dict[int, dict[str, list[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )
        repeated_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
        rows = self.repository.list_page_state_rows(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
            field_specs=field_specs,
        )
        for row in rows:
            specs = specs_by_binding_id.get(
                int(row["event_form_binding_id"] or 0),
            )
            if not specs:
                specs = specs_by_event_form.get(
                    (
                        int(row["visit__event_definition_id"] or 0),
                        int(row["crf_template_id"]),
                    ),
                    (),
                )
            if not specs:
                continue

            values_by_field_key: dict[str, list[Any]] = defaultdict(list)
            for field_value in self._read_field_values(row):
                values_by_field_key[field_value.field_key].append(
                    field_value.value
                )
            subject_id = int(row["subject_id"])
            if any(
                bool(spec.get("is_repeatable_within_event"))
                for spec in specs
            ):
                repeated_row = {
                    spec["token"]: self._collapse_values(
                        self._decoded_field_values(
                            values_by_field_key=values_by_field_key,
                            spec=spec,
                        )
                    )
                    for spec in specs
                }
                if any(
                    value not in (None, "")
                    for value in repeated_row.values()
                ):
                    repeated_rows[subject_id].append(repeated_row)
                continue

            for spec in specs:
                base_values[subject_id][spec["token"]].extend(
                    self._decoded_field_values(
                        values_by_field_key=values_by_field_key,
                        spec=spec,
                    )
                )

        result = {}
        for subject_id in base_values.keys() | repeated_rows.keys():
            collapsed_base_values = {
                token: self._collapse_values(values)
                for token, values in base_values[subject_id].items()
            }
            subject_repeated_rows = repeated_rows.get(subject_id, ())
            if subject_repeated_rows:
                result[subject_id] = tuple(
                    {
                        **collapsed_base_values,
                        **repeated_row,
                    }
                    for repeated_row in subject_repeated_rows
                )
            else:
                result[subject_id] = (collapsed_base_values,)
        return result

    @classmethod
    def _decoded_field_values(
        cls,
        *,
        values_by_field_key: dict[str, list[Any]],
        spec: dict,
    ) -> list[Any]:
        return [
            cls._decode_choice_value(value, spec=spec)
            for value in values_by_field_key.get(spec["field_key"], ())
        ]

    @classmethod
    def _decode_choice_value(cls, raw_value, *, spec: dict):
        control_type = (
            str(spec.get("control_type") or "")
            .strip()
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )
        if control_type not in {
            "RADIO",
            "RADIO_BUTTON_LIST",
            "CHECKBOX",
            "CHECKBOX_LIST",
        }:
            return raw_value
        choice_labels = {
            str(value).strip(): str(label).strip()
            for value, label in (spec.get("choice_labels") or {}).items()
            if str(value).strip() and str(label).strip()
        }
        if not choice_labels or raw_value in (None, ""):
            return raw_value

        selected_values = cls._normalize_selected_choice_values(raw_value)
        labels_by_casefold = {
            value.casefold(): label
            for value, label in choice_labels.items()
        }
        decoded_values = []
        for value in selected_values:
            normalized_value = str(value).strip()
            decoded_values.append(
                choice_labels.get(
                    normalized_value,
                    labels_by_casefold.get(
                        normalized_value.casefold(),
                        normalized_value,
                    ),
                )
            )
        return ", ".join(decoded_values) if decoded_values else raw_value

    @staticmethod
    def _normalize_selected_choice_values(raw_value) -> list[Any]:
        if isinstance(raw_value, (list, tuple, set)):
            return list(raw_value)
        if isinstance(raw_value, str):
            normalized = raw_value.strip()
            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return parsed
            if "," in normalized:
                return [
                    value.strip()
                    for value in normalized.split(",")
                    if value.strip()
                ]
        return [raw_value]

    @classmethod
    def _read_field_values(cls, row: dict):
        raw_payload = cls._resolve_raw_payload(
            final_data=row.get("final_data"),
            current_entry_data=row.get("current_entry__data"),
        )
        if not raw_payload:
            return ()
        try:
            parsed = (
                raw_payload
                if isinstance(raw_payload, dict)
                else json.loads(raw_payload)
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return ()
        if not isinstance(parsed, dict):
            return ()
        return tuple(
            iter_field_values(
                normalize_form_data(parsed, strict=False),
            )
        )

    @classmethod
    def _resolve_raw_payload(cls, *, final_data, current_entry_data):
        if cls._has_meaningful_data(final_data):
            return final_data
        return current_entry_data

    @staticmethod
    def _has_meaningful_data(raw_data) -> bool:
        if isinstance(raw_data, (dict, list)):
            decoded_data = raw_data
        else:
            normalized_data = str(raw_data or "").strip()
            if not normalized_data:
                return False
            try:
                decoded_data = json.loads(normalized_data)
            except (TypeError, json.JSONDecodeError):
                return True
        if isinstance(decoded_data, dict) and decoded_data.get("format") == "edc.form_data.v1":
            groups = decoded_data.get("groups")
            if not isinstance(groups, dict):
                return False
            return any(
                (
                    isinstance(group, dict)
                    and (
                        bool(group.get("items"))
                        or bool(group.get("rows"))
                    )
                )
                for group in groups.values()
            )
        if isinstance(decoded_data, (dict, list)):
            return bool(decoded_data)
        return decoded_data is not None

    @classmethod
    def _collapse_values(cls, values: list[Any]):
        normalized = [
            cls._normalize_cell_value(value)
            for value in values
            if value not in (None, "")
        ]
        if not normalized:
            return ""
        if len(normalized) == 1:
            return normalized[0]
        return json.dumps(normalized, ensure_ascii=False, default=str)

    @staticmethod
    def _normalize_cell_value(value):
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return value


__all__ = ["SubjectExportDataService"]
