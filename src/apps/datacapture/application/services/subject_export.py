import json
from collections import defaultdict
from typing import Any

from apps.core.form_data_document import iter_field_values, normalize_form_data
from apps.datacapture.infrastructure.repositories.subject_export import (
    DjangoSubjectExportDataRepository,
)

_VISIT_SORT_KEY = "__export_visit_sort_key__"


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

        values_by_subject_and_visit: dict[
            int, dict[tuple[int, int, int], dict[str, list[Any]]]
        ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        visit_row_metadata: dict[int, dict[tuple[int, int, int], tuple]] = defaultdict(
            dict,
        )
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
            visit_scope = self._resolve_visit_scope(row)
            visit_row_metadata[subject_id].setdefault(
                visit_scope,
                self._visit_metadata_from_row(row=row),
            )

            for spec in specs:
                values_by_subject_and_visit[subject_id][visit_scope][
                    spec["token"]
                ].extend(
                    self._decoded_field_values(
                        values_by_field_key=values_by_field_key,
                        spec=spec,
                    )
                )

        result = {}
        for subject_id in values_by_subject_and_visit.keys():
            visit_rows = values_by_subject_and_visit[subject_id]
            sorted_scopes = sorted(
                visit_rows.keys(),
                key=lambda scope: visit_row_metadata[subject_id].get(scope, ()),
            )
            subject_result = []
            for scope in sorted_scopes:
                collapsed_base_values = {
                    token: self._collapse_values(values)
                    for token, values in visit_rows[scope].items()
                }
                collapsed_base_values[_VISIT_SORT_KEY] = visit_row_metadata[
                    subject_id
                ].get(scope, ())
                subject_result.append(collapsed_base_values)
            result[subject_id] = tuple(subject_result)
        return result

    @staticmethod
    def _resolve_visit_scope(row: dict) -> tuple[int, int, int]:
        return (
            int(row.get("visit__event_definition__sequence_no") or 0),
            int(row.get("visit__repeat_index") or 0),
            int(row.get("visit_id") or 0),
        )

    @staticmethod
    def _visit_metadata_from_row(row: dict) -> tuple:
        return (
            int(row.get("visit__event_definition__sequence_no") or 0),
            int(row.get("visit__repeat_index") or 0),
            int(row.get("visit_id") or 0),
            int(row.get("repeat_index") or 0),
            int(row.get("id") or 0),
        )

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
        return "; ".join(str(value) for value in normalized)

    @staticmethod
    def _normalize_cell_value(value):
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return value


__all__ = ["SubjectExportDataService"]
