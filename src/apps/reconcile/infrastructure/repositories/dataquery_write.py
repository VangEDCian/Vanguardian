import json
import re
from datetime import datetime

from django.db.models import F, Q
from django.utils.translation import get_language

from apps.core.choices import DataCapturePageEntryStatusChoices
from apps.core.form_data_document import (
    build_field_path,
    flatten_form_data_for_export,
    normalize_form_data,
)
from apps.crf.models import CrfFieldTemplate
from apps.datacapture.models import DataCapturePageEntry
from apps.reconcile.models import (
    ReconcileDataQuery,
    ReconcileDataQuerySeverityChoices,
    ReconcileDataQuerySourceChoices,
    ReconcileDataQueryStatusChoices,
    ReconcileDataQueryTypeChoices,
    ReconcileQueryThread,
    ReconcileQueryThreadSourceChoices,
    ReconcileQueryThreadVisibilityChoices,
)

_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")
_JSONPATH_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DjangoReconcileDataQueryWriteRepository:
    @staticmethod
    def list_field_key_to_id(*, crf_template_id: int) -> dict[str, int]:
        return dict(
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                deleted=False,
            ).values_list("field_key", "id"),
        )

    @staticmethod
    def list_field_thread_value_contexts(
        *,
        crf_template_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, dict[str, object]]:
        if not field_template_ids:
            return {}
        current_language = str(get_language() or "").split("-")[0].lower()
        fields = (
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                id__in=field_template_ids,
                deleted=False,
            )
            .select_related("ui_config")
            .prefetch_related("ui_config__translations")
        )
        contexts: dict[int, dict[str, object]] = {}
        for field in fields:
            ui_config = getattr(field, "ui_config", None)
            if ui_config is None or ui_config.deleted:
                continue
            translations = list(getattr(getattr(ui_config, "translations", None), "all", lambda: [])())
            preferred_translation = next(
                (
                    translation
                    for translation in translations
                    if str(translation.language_code or "").split("-")[0].lower() == current_language
                    and translation.options
                ),
                None,
            )
            fallback_translation = next((translation for translation in translations if translation.options), None)
            translation = preferred_translation or fallback_translation
            contexts[field.pk] = {
                "control_type": ui_config.control_type,
                "options": getattr(translation, "options", "") if translation is not None else "",
            }
        return contexts

    @classmethod
    def bulk_create_manual_open_queries(
        cls,
        *,
        page_state_id: int,
        items: list[dict[str, object]],
        actor_user_id: int | None,
        now: datetime,
    ) -> int:
        records: list[ReconcileDataQuery] = []
        for item in items:
            field_template_id = item.get("field_template_id")
            entry_context = cls._current_page_entry_query_context(
                page_state_id=page_state_id,
                field_template_id=int(field_template_id) if field_template_id is not None else None,
            )
            records.append(
                ReconcileDataQuery(
                    created_at=now,
                    updated_at=now,
                    deleted=False,
                    status=ReconcileDataQueryStatusChoices.OPEN,
                    source=ReconcileDataQuerySourceChoices.MANUAL,
                    query_type=ReconcileDataQueryTypeChoices.MANUAL,
                    severity=ReconcileDataQuerySeverityChoices.MINOR,
                    is_blocking=True,
                    question_text=str(item.get("reason") or ""),
                    resolution_note=str(item.get("resolution_note") or "")[:1000],
                    opened_at=now,
                    closed_at=None,
                    page_state_id=page_state_id,
                    page_entry_id=entry_context.get("page_entry_id"),
                    field_template_id=item.get("field_template_id"),
                    validation_rule_id=None,
                    data_version=entry_context.get("data_version") or item.get("data_version"),
                    field_path=entry_context.get("field_path") or item.get("field_path"),
                    value_snapshot=entry_context.get("value_snapshot"),
                    assigned_to_id=entry_context.get("assigned_to_id"),
                    opened_by_id=actor_user_id,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                ),
            )
        if not records:
            return 0
        ReconcileDataQuery.objects.bulk_create(records)
        return len(records)

    @classmethod
    def has_open_query_for_page_field(
        cls,
        *,
        page_state_id: int,
        field_template_id: int,
        field_key: str = "",
    ) -> bool:
        entry_context = cls._current_page_entry_query_context(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            storage_key_hint=field_key,
        )
        queryset = ReconcileDataQuery.objects.filter(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            status=ReconcileDataQueryStatusChoices.OPEN,
            deleted=False,
        )
        field_path = str(entry_context.get("field_path") or "").strip()
        if field_path:
            field_paths = [
                str(path or "").strip()
                for path in entry_context.get("field_path_candidates", (field_path,))
                if str(path or "").strip()
            ]
            queryset = queryset.filter(field_path__in=field_paths or [field_path])
        return queryset.exists()

    @staticmethod
    def list_latest_open_query_ids_by_page_state_and_field_templates(
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, int]:
        if not field_template_ids:
            return {}
        rows = (
            ReconcileDataQuery.objects.filter(
                page_state_id=page_state_id,
                field_template_id__in=field_template_ids,
                field_template_id__isnull=False,
                status=ReconcileDataQueryStatusChoices.OPEN,
                deleted=False,
            )
            .order_by("field_template_id", "-opened_at", "-created_at", "-id")
            .values("field_template_id", "id")
        )
        query_ids_by_field_template: dict[int, int] = {}
        for row in rows:
            query_ids_by_field_template.setdefault(int(row["field_template_id"]), int(row["id"]))
        return query_ids_by_field_template

    @classmethod
    def create_manual_open_query(
        cls,
        *,
        page_state_id: int,
        field_template_id: int,
        question_text: str,
        actor_user_id: int | None,
        now: datetime,
        field_key: str = "",
    ) -> ReconcileDataQuery:
        entry_context = cls._current_page_entry_query_context(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            storage_key_hint=field_key,
        )
        return ReconcileDataQuery.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            status=ReconcileDataQueryStatusChoices.OPEN,
            source=ReconcileDataQuerySourceChoices.MANUAL,
            query_type=ReconcileDataQueryTypeChoices.MANUAL,
            severity=ReconcileDataQuerySeverityChoices.MINOR,
            is_blocking=True,
            question_text=question_text,
            resolution_note="",
            opened_at=now,
            closed_at=None,
            page_state_id=page_state_id,
            page_entry_id=entry_context.get("page_entry_id"),
            field_template_id=field_template_id,
            validation_rule_id=None,
            data_version=entry_context.get("data_version"),
            field_path=entry_context.get("field_path"),
            value_snapshot=entry_context.get("value_snapshot"),
            assigned_to_id=entry_context.get("assigned_to_id"),
            opened_by_id=actor_user_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    @staticmethod
    def create_query_thread_message(
        *,
        dataquery_id: int,
        message_text: str,
        message_type: str,
        actor_user_id: int | None,
        now: datetime,
        source: str = ReconcileQueryThreadSourceChoices.MANUAL,
    ) -> ReconcileQueryThread:
        return ReconcileQueryThread.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            message_text=message_text,
            message_type=message_type,
            visibility=ReconcileQueryThreadVisibilityChoices.SITE,
            source=source,
            dataquery_id=dataquery_id,
            author_id=actor_user_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    @staticmethod
    def close_query(
        *,
        dataquery_id: int,
        page_state_id: int,
        field_template_id: int,
        resolution_note: str,
        actor_user_id: int | None,
        now: datetime,
        is_resolved: bool,
    ) -> bool:
        if is_resolved is not True:
            return False
        updated = (
            ReconcileDataQuery.objects.filter(
                pk=dataquery_id,
                page_state_id=page_state_id,
                field_template_id=field_template_id,
                deleted=False,
            )
            .exclude(status__in=(ReconcileDataQueryStatusChoices.CANCELLED, ReconcileDataQueryStatusChoices.CLOSED))
            .update(
                status=ReconcileDataQueryStatusChoices.CLOSED,
                resolution_note=resolution_note[:1000],
                resolved_at=now,
                resolved_by_id=F("answered_by_id"),
                closed_at=now,
                closed_by_id=actor_user_id,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
        )
        return updated > 0

    @staticmethod
    def mark_query_answered(
        *,
        dataquery_id: int,
        page_state_id: int,
        field_template_id: int,
        actor_user_id: int | None,
        now: datetime,
    ) -> bool:
        updated = (
            ReconcileDataQuery.objects.filter(
                pk=dataquery_id,
                page_state_id=page_state_id,
                field_template_id=field_template_id,
                deleted=False,
            )
            .exclude(status__in=(ReconcileDataQueryStatusChoices.CANCELLED, ReconcileDataQueryStatusChoices.CLOSED))
            .update(
                answered_at=now,
                answered_by_id=actor_user_id,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
        )
        return updated > 0

    @staticmethod
    def cancel_query(
        *,
        dataquery_id: int,
        page_state_id: int,
        field_template_id: int,
        actor_user_id: int | None,
        now: datetime,
    ) -> bool:
        updated = (
            ReconcileDataQuery.objects.filter(
                pk=dataquery_id,
                page_state_id=page_state_id,
                field_template_id=field_template_id,
                deleted=False,
            )
            .exclude(status__in=(ReconcileDataQueryStatusChoices.CANCELLED, ReconcileDataQueryStatusChoices.CLOSED))
            .update(
                status=ReconcileDataQueryStatusChoices.CANCELLED,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
        )
        return updated > 0

    @staticmethod
    def query_belongs_to_scope(*, dataquery_id: int, page_state_id: int, field_template_id: int) -> bool:
        return ReconcileDataQuery.objects.filter(
            pk=dataquery_id,
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            deleted=False,
        ).exists()

    @staticmethod
    def user_can_respond_to_query(*, dataquery_id: int, actor_user_id: int | None) -> bool:
        if actor_user_id is None:
            return False
        return ReconcileDataQuery.objects.filter(
            pk=dataquery_id,
            deleted=False,
        ).filter(
            Q(opened_by_id=actor_user_id) | Q(assigned_to_id=actor_user_id),
        ).exists()

    @classmethod
    def _current_page_entry_query_context(
        cls,
        *,
        page_state_id: int,
        field_template_id: int | None,
        storage_key_hint: str = "",
    ) -> dict[str, object]:
        if field_template_id is None:
            return {}
        entry = (
            DataCapturePageEntry.objects.filter(
                page_state_id=page_state_id,
                page_state__current_entry_id=F("id"),
                deleted=False,
            )
            .only("id", "entry_version", "data", "submitted_by_id")
            .first()
        )
        if entry is None:
            entry = (
                DataCapturePageEntry.objects.filter(
                    page_state_id=page_state_id,
                    status=DataCapturePageEntryStatusChoices.SUBMITTED,
                    deleted=False,
                )
                .order_by("-submitted_at", "-updated_at", "-id")
                .only("id", "entry_version", "data", "submitted_by_id")
                .first()
            )
        if entry is None:
            return {}

        field = (
            CrfFieldTemplate.objects.filter(pk=field_template_id, deleted=False)
            .select_related("section_template")
            .only("field_key", "section_template__section_code", "section_template__is_repeatable")
            .first()
        )
        field_key = str(getattr(field, "field_key", "") or "").strip()
        section_code = str(getattr(getattr(field, "section_template", None), "section_code", "") or "").strip()
        is_repeatable = bool(getattr(getattr(field, "section_template", None), "is_repeatable", False))
        storage_key_hint = str(storage_key_hint or "").strip()
        payload = cls._parse_entry_payload(entry.data)
        value_snapshot, storage_key = cls._entry_field_value_snapshot(
            payload=payload,
            field_key=field_key,
            field_template_id=field_template_id,
            storage_key_hint=storage_key_hint,
        )
        field_path = cls._canonical_field_path(
            section_code=section_code,
            storage_key=storage_key,
            is_repeatable=is_repeatable,
        )
        return {
            "page_entry_id": entry.pk,
            "data_version": str(entry.entry_version or "").strip() or None,
            "field_path": field_path,
            "field_path_candidates": cls._field_path_candidates(
                section_code=section_code,
                storage_key=storage_key,
                is_repeatable=is_repeatable,
                field_path=field_path,
            ),
            "value_snapshot": value_snapshot,
            "assigned_to_id": entry.submitted_by_id,
        }

    @staticmethod
    def _parse_entry_payload(raw_data: object) -> dict[str, object]:
        if isinstance(raw_data, dict):
            return raw_data
        try:
            parsed = json.loads(str(raw_data or "{}"))
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        doc = normalize_form_data(parsed, strict=False)
        return flatten_form_data_for_export(doc, repeat_strategy="legacy_repeat_suffix")

    @classmethod
    def _entry_field_value_snapshot(
        cls,
        *,
        payload: dict[str, object],
        field_key: str,
        field_template_id: int,
        storage_key_hint: str = "",
    ) -> tuple[str, str]:
        storage_keys = cls._candidate_storage_keys(
            field_key=field_key,
            field_template_id=field_template_id,
            storage_key_hint=storage_key_hint,
        )
        for storage_key in storage_keys:
            if storage_key in payload:
                return cls._format_value_snapshot(payload.get(storage_key)), storage_key
        for storage_key in storage_keys:
            part_map = {
                f"{storage_key}{suffix}": payload.get(f"{storage_key}{suffix}")
                for suffix in _DATE_PART_SUFFIXES
                if f"{storage_key}{suffix}" in payload
            }
            if part_map:
                return json.dumps(part_map, ensure_ascii=False, sort_keys=True), storage_key
        fallback_key = storage_key_hint or field_key or f"field_{field_template_id}"
        return "", fallback_key

    @staticmethod
    def _candidate_storage_keys(
        *,
        field_key: str,
        field_template_id: int,
        storage_key_hint: str = "",
    ) -> list[str]:
        keys = [
            key
            for key in (
                storage_key_hint,
                field_key,
                f"field_{field_template_id}",
            )
            if key
        ]
        ordered: list[str] = []
        seen: set[str] = set()
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
        return ordered

    @staticmethod
    def _format_value_snapshot(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    @staticmethod
    def _jsonpath_for_field_key(field_key: str) -> str:
        normalized = str(field_key or "").strip()
        if not normalized:
            return "$"
        if _JSONPATH_IDENTIFIER_PATTERN.match(normalized):
            return f"$.{normalized}"
        return f"$[{json.dumps(normalized, ensure_ascii=False)}]"

    @classmethod
    def _canonical_field_path(cls, *, section_code: str, storage_key: str, is_repeatable: bool = False) -> str:
        if not section_code:
            return cls._jsonpath_for_field_key(storage_key)
        repeat_match = re.match(r"^(?P<base>.+)__repeat_(?P<repeat_index>\d+)$", str(storage_key or "").strip())
        if repeat_match:
            row_no = int(repeat_match.group("repeat_index"))
            return build_field_path(
                section_code,
                repeat_match.group("base"),
                row_key=f"row_{row_no:03d}",
            )
        if is_repeatable:
            return build_field_path(section_code, storage_key, row_key="row_001")
        return build_field_path(section_code, storage_key)

    @classmethod
    def _field_path_candidates(
        cls,
        *,
        section_code: str,
        storage_key: str,
        is_repeatable: bool,
        field_path: str,
    ) -> tuple[str, ...]:
        candidates = [str(field_path or "").strip()]
        if section_code and is_repeatable and not re.match(r"^.+__repeat_\d+$", str(storage_key or "").strip()):
            candidates.append(build_field_path(section_code, storage_key))
        return tuple(key for key in dict.fromkeys(candidates) if key)


__all__ = ["DjangoReconcileDataQueryWriteRepository"]
