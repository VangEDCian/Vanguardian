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
    ) -> dict[int, dict[str, Any]]:
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

        collected: dict[int, dict[str, list[Any]]] = defaultdict(
            lambda: defaultdict(list)
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
            for spec in specs:
                collected[subject_id][spec["token"]].extend(
                    values_by_field_key.get(spec["field_key"], ())
                )

        return {
            subject_id: {
                token: self._collapse_values(values)
                for token, values in values_by_token.items()
            }
            for subject_id, values_by_token in collected.items()
        }

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
