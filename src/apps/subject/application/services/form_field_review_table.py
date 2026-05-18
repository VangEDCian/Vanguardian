import json
from datetime import date, datetime
from typing import Any

from django.utils import formats, timezone

from apps.reconcile.application.services.dataquery_read import ReconcileDataQueryReadService
from apps.subject.infrastructure.repositories.event_instance_schedule_read import (
    DjangoSubjectEventInstanceScheduleReadRepository,
)
from apps.subject.infrastructure.repositories.user_display_lookup import get_username_display_for_user_id

_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")


def _normalize_storage_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return str(value).strip()


class FormFieldReviewTableService:

    def __init__(self, reconcile_read_service=None):
        self._reconcile_read_service = reconcile_read_service or ReconcileDataQueryReadService()

    def build_for_verification(
        self,
        *,
        subject_code: str,
        site_id: int,
        event_name: str,
        event_instance_id: int,
        form_name: str,
        form_status: str,
        entry_version: str,
        entry_updated_at: datetime | None,
        entry_updated_by_id: int | None,
        field_templates_payload: list[dict[str, Any]],
        entry_payload: dict[str, Any],
        page_state_id: int | None,
        current_user_id: int | None = None,
        verified_snapshot: dict[str, Any] | None = None,
        verified_field_template_ids: set[int] | None = None,
    ) -> dict[str, Any]:
        event_start_at = DjangoSubjectEventInstanceScheduleReadRepository().get_event_start_datetime(
            event_instance_id=event_instance_id,
        )
        field_template_ids: list[int] = []
        for field_row in field_templates_payload or []:
            raw_id = field_row.get("id")
            try:
                field_template_ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        counts: dict[int, int] = {}
        active_query_ids: dict[int, int] = {}
        query_thread_badge_counts: dict[int, int] = {}
        query_messages_by_field: dict[int, list[dict[str, Any]]] = {}
        if page_state_id is not None and field_template_ids:
            counts = self._reconcile_read_service.count_open_queries_by_page_state_and_field_templates(
                page_state_id=page_state_id,
                field_template_ids=tuple(field_template_ids),
            )
            active_query_ids = (
                self._reconcile_read_service.list_latest_active_query_ids_by_page_state_and_field_templates(
                    page_state_id=page_state_id,
                    field_template_ids=tuple(field_template_ids),
                )
            )
            query_thread_badge_counts = (
                self._reconcile_read_service.count_query_threads_since_current_user_last_comment(
                    page_state_id=page_state_id,
                    field_template_ids=tuple(field_template_ids),
                    current_user_id=current_user_id,
                )
            )
            query_messages_by_field = (
                self._reconcile_read_service.list_latest_query_messages_by_page_state_and_field_templates(
                    page_state_id=page_state_id,
                    field_template_ids=tuple(field_template_ids),
                    limit_per_field=10,
                )
            )

        modified_by_display = get_username_display_for_user_id(entry_updated_by_id)

        rows: list[dict[str, Any]] = []
        for field_row in field_templates_payload or []:
            try:
                field_template_id = int(field_row.get("id"))
            except (TypeError, ValueError):
                continue
            field_key = str(field_row.get("field_key") or "").strip()
            brief = str(field_row.get("label") or field_key or "—")
            ui_config = field_row.get("ui_config") if isinstance(field_row.get("ui_config"), dict) else {}
            control_norm = self._normalize_control_type(ui_config.get("control_type"))
            options_raw = ui_config.get("options")
            label_by_value = self._options_value_label_map(options_raw)
            raw_value = self._resolve_entry_value_for_field(
                entry_payload,
                field_key=field_key,
                field_template_id=field_template_id,
            )
            display_value = self._resolve_display_value(
                raw_value=raw_value,
                control_norm=control_norm,
                label_by_value=label_by_value,
            )
            is_checked = False
            if verified_field_template_ids is not None:
                is_checked = field_template_id in verified_field_template_ids
            elif verified_snapshot is not None:
                is_checked = self.field_storage_matches_snapshot(
                    verified_snapshot,
                    entry_payload,
                    field_key=field_key,
                    field_template_id=field_template_id,
                )
            rows.append(
                {
                    "field_template_id": field_template_id,
                    "field_key": field_key,
                    "brief_description": brief,
                    "data_type": str(field_row.get("data_type") or "").strip(),
                    "unit": str(field_row.get("unit") or "").strip(),
                    "precision": field_row.get("precision"),
                    "raw_value": raw_value,
                    "display_value": display_value,
                    "open_query_count": int(counts.get(field_template_id, 0)),
                    "active_query_id": active_query_ids.get(field_template_id),
                    "query_thread_badge_count": int(query_thread_badge_counts.get(field_template_id, 0)),
                    "query_messages": self._format_query_messages(
                        query_messages_by_field.get(field_template_id, []),
                    ),
                    "modified_by": modified_by_display,
                    "is_checked": is_checked,
                },
            )

        return {
            "header": {
                "subject_code": subject_code or "—",
                "event_name": event_name or "—",
                "site_id": str(site_id) if site_id is not None else "—",
                "event_start_date": self._format_datetime(event_start_at),
                "form_name": form_name or "—",
                "form_status": (form_status or "").strip() or "—",
                "form_version": (entry_version or "").strip() or "—",
                "last_modified": self._format_datetime(entry_updated_at),
            },
            "rows": rows,
        }

    @classmethod
    def storage_keys_for_field(cls, field_key: str, field_template_id: int) -> list[str]:
        bases: list[str] = []
        fk = str(field_key or "").strip()
        if fk:
            bases.append(fk)
        bases.append(f"field_{int(field_template_id)}")
        ordered: list[str] = []
        seen: set[str] = set()
        for base in bases:
            candidates = [base, *[f"{base}{suffix}" for suffix in _DATE_PART_SUFFIXES]]
            for k in candidates:
                if k not in seen:
                    seen.add(k)
                    ordered.append(k)
        return ordered

    @classmethod
    def slice_payload_for_field(
        cls,
        payload: dict[str, Any],
        *,
        field_key: str,
        field_template_id: int,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        out: dict[str, Any] = {}
        for k in cls.storage_keys_for_field(field_key, field_template_id):
            if k in payload:
                out[k] = payload[k]
        return out

    @classmethod
    def all_form_storage_keys(cls, field_templates_payload: list[dict[str, Any]]) -> set[str]:
        keys: set[str] = set()
        for field_row in field_templates_payload or []:
            try:
                tid = int(field_row.get("id"))
            except (TypeError, ValueError):
                continue
            fk = str(field_row.get("field_key") or "").strip()
            keys.update(cls.storage_keys_for_field(fk, tid))
        return keys

    @classmethod
    def field_storage_matches_snapshot(
        cls,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        *,
        field_key: str,
        field_template_id: int,
    ) -> bool:
        a = cls.slice_payload_for_field(snapshot, field_key=field_key, field_template_id=field_template_id)
        b = cls.slice_payload_for_field(entry, field_key=field_key, field_template_id=field_template_id)
        return cls._storage_slices_equal(a, b)

    @classmethod
    def all_fields_verified_against_entry(
        cls,
        *,
        final_payload: dict[str, Any],
        entry_payload: dict[str, Any],
        field_templates_payload: list[dict[str, Any]],
    ) -> bool:
        for field_row in field_templates_payload or []:
            try:
                tid = int(field_row.get("id"))
            except (TypeError, ValueError):
                continue
            fk = str(field_row.get("field_key") or "").strip()
            if not cls.field_storage_matches_snapshot(final_payload, entry_payload, field_key=fk, field_template_id=tid):
                return False
        return True

    @classmethod
    def _storage_slices_equal(cls, a: dict[str, Any], b: dict[str, Any]) -> bool:
        keys = set(a) | set(b)
        for k in keys:
            if _normalize_storage_scalar(a.get(k)) != _normalize_storage_scalar(b.get(k)):
                return False
        return True

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "—"
        local_value = timezone.localtime(value) if timezone.is_aware(value) else value
        return formats.date_format(local_value, format="SHORT_DATETIME_FORMAT", use_l10n=True)

    @classmethod
    def _format_query_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for message in messages[:10]:
            opened_by_id = message.get("opened_by_id")
            opened_by = get_username_display_for_user_id(opened_by_id)
            timestamp = message.get("opened_at") or message.get("created_at")
            out.append(
                {
                    "dataquery_id": message.get("dataquery_id"),
                    "text": str(message.get("text") or "").strip(),
                    "status": str(message.get("status") or "").strip(),
                    "opened_by": opened_by,
                    "opened_at": cls._format_datetime(timestamp),
                },
            )
        return out

    @staticmethod
    def _normalize_control_type(control_type: object) -> str:
        raw = str(control_type or "").strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "textbox": "text",
            "entry_box": "text",
            "numeric": "number",
            "date_picker": "date",
            "time_picker": "datetime",
            "textarea": "free_text",
            "dropdown": "select",
            "dropdown_list": "select",
            "radio_button_list": "radio",
            "checkbox_list": "multi_select",
        }
        normalized = aliases.get(raw, raw)
        if normalized == "textarea":
            return "free_text"
        return normalized

    @staticmethod
    def _resolve_stored_value(payload: dict[str, Any], canonical_key: str) -> Any:
        if not canonical_key or not payload:
            return None
        date_keys = [f"{canonical_key}{suffix}" for suffix in _DATE_PART_SUFFIXES]
        if any(k in payload for k in date_keys):
            return {
                "__day": payload.get(f"{canonical_key}__day"),
                "__month": payload.get(f"{canonical_key}__month"),
                "__year": payload.get(f"{canonical_key}__year"),
                "__time": payload.get(f"{canonical_key}__time"),
            }
        return payload.get(canonical_key)

    @classmethod
    def _resolve_entry_value_for_field(
        cls,
        payload: dict[str, Any],
        *,
        field_key: str,
        field_template_id: int,
    ) -> Any:
        if not payload:
            return None
        if field_key:
            value = cls._resolve_stored_value(payload, field_key)
            if value is not None:
                return value
        alt_key = f"field_{field_template_id}"
        return cls._resolve_stored_value(payload, alt_key)

    @staticmethod
    def _is_date_parts_dict(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        return any(k in value for k in ("__day", "__month", "__year", "__time"))

    @staticmethod
    def _format_date_part_map(value: dict[str, Any]) -> str:
        day = str(value.get("__day") or "").strip()
        month = str(value.get("__month") or "").strip()
        year = str(value.get("__year") or "").strip()
        time_part = str(value.get("__time") or "").strip()
        if not (day or month or year) and not time_part:
            return "—"
        try:
            if year and month and day:
                d = date(int(year), int(month), int(day))
                out = formats.date_format(d, format="SHORT_DATE_FORMAT", use_l10n=True)
                return f"{out} {time_part}".strip() if time_part else out
        except (ValueError, TypeError):
            pass
        parts = [p for p in (day, month, year) if p]
        base = " / ".join(parts) if parts else "—"
        return f"{base} {time_part}".strip() if time_part else base

    @staticmethod
    def _parse_options_list(parsed: Any) -> list[Any]:
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("static", "choices", "options", "items"):
                inner = parsed.get(key)
                if isinstance(inner, list):
                    return inner
        return []

    def _options_value_label_map(self, options_raw: object) -> dict[str, str]:
        if options_raw in (None, ""):
            return {}
        if isinstance(options_raw, (list, dict)):
            parsed = options_raw
        else:
            text = str(options_raw).strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except (TypeError, ValueError, json.JSONDecodeError):
                return {}
        out: dict[str, str] = {}
        for item in self._parse_options_list(parsed):
            if not isinstance(item, dict):
                continue
            value = item.get("value", item.get("code", item.get("id", "")))
            value_key = "" if value is None else str(value).strip()
            label = item.get("label", item.get("text", value_key))
            label_text = "" if label is None else str(label).strip()
            if value_key:
                out[value_key] = label_text or value_key
        return out

    def _resolve_display_value(
        self,
        *,
        raw_value: Any,
        control_norm: str,
        label_by_value: dict[str, str],
    ) -> str:
        raw_types = {
            "text",
            "number",
            "date",
            "free_text",
            "datetime",
            "label_only",
        }
        option_types = {"checkbox", "radio", "select", "multi_select"}
        if control_norm in raw_types:
            return self._raw_display_value(raw_value)
        if control_norm in option_types:
            return self._map_options_value(raw_value, label_by_value, control_norm)
        return self._raw_display_value(raw_value)

    @staticmethod
    def _raw_display_value(raw_value: Any) -> str:
        if raw_value is None:
            return "—"
        if FormFieldReviewTableService._is_date_parts_dict(raw_value):
            return FormFieldReviewTableService._format_date_part_map(raw_value)
        if isinstance(raw_value, bool):
            return "true" if raw_value else "false"
        if isinstance(raw_value, (list, dict)):
            text = json.dumps(raw_value, ensure_ascii=False)
            return text if text else "—"
        text = str(raw_value).strip()
        return text if text else "—"

    def _map_options_value(
        self,
        raw_value: Any,
        label_by_value: dict[str, str],
        control_norm: str,
    ) -> str:
        if not label_by_value:
            return self._raw_display_value(raw_value)
        if FormFieldReviewTableService._is_date_parts_dict(raw_value):
            return self._raw_display_value(raw_value)
        tokens = self._storage_tokens(raw_value)
        if not tokens:
            return "—"
        if control_norm in {"checkbox", "multi_select"} and len(tokens) > 1:
            labels = [label_by_value.get(t, t) for t in tokens]
            joined = ", ".join(labels)
            return joined if joined else "—"
        primary = tokens[0]
        return label_by_value.get(primary, self._raw_display_value(raw_value))

    @staticmethod
    def _storage_tokens(raw_value: Any) -> list[str]:
        if raw_value is None:
            return []
        if isinstance(raw_value, bool):
            return ["true"] if raw_value else ["false"]
        if isinstance(raw_value, list):
            return ["" if v is None else str(v).strip() for v in raw_value if str(v).strip() != ""]
        if isinstance(raw_value, dict):
            return [json.dumps(raw_value, ensure_ascii=False)]
        text = str(raw_value).strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                loaded = json.loads(text)
            except (TypeError, ValueError, json.JSONDecodeError):
                loaded = None
            if isinstance(loaded, list):
                return FormFieldReviewTableService._storage_tokens(loaded)
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip() != ""]
        return [text]


__all__ = ["FormFieldReviewTableService"]
