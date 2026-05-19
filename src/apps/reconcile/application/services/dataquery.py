import json
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.reconcile.infrastructure.repositories import DjangoReconcileDataQueryWriteRepository
from apps.reconcile.models import ReconcileQueryThreadSourceChoices

_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")
_QUERY_THREAD_COMMENT = "comment"
_QUERY_THREAD_RESOLUTION = "resolution"


@dataclass(frozen=True)
class ReconcileChangeReasonItem:
    field_key: str
    field_label: str
    reason: str


class ReconcileDataQueryWriteService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoReconcileDataQueryWriteRepository()

    @staticmethod
    def _canonical_field_key(field_key: str) -> str:
        normalized = str(field_key or "").strip()
        for suffix in _DATE_PART_SUFFIXES:
            if normalized.endswith(suffix):
                return normalized[: -len(suffix)]
        return normalized

    @staticmethod
    def _resolve_field_template_id(*, canonical_field_key: str, field_key_to_id: dict[str, int]) -> int | None:
        if not canonical_field_key:
            return None
        if canonical_field_key.startswith("field_"):
            raw_id = canonical_field_key.removeprefix("field_").strip()
            if raw_id.isdigit():
                return int(raw_id)
        return field_key_to_id.get(canonical_field_key)

    def create_change_reason_data_queries(
        self,
        *,
        page_state_id: int,
        crf_template_id: int,
        reasons: list[ReconcileChangeReasonItem],
        actor_user_id: int | None,
    ) -> int:
        normalized_reasons: list[ReconcileChangeReasonItem] = []
        for item in reasons:
            field_key = self._canonical_field_key(item.field_key)
            reason = str(item.reason or "").strip()
            if not field_key or not reason:
                continue
            normalized_reasons.append(
                ReconcileChangeReasonItem(
                    field_key=field_key,
                    field_label=str(item.field_label or "").strip(),
                    reason=reason,
                )
            )

        if not normalized_reasons:
            return 0

        field_key_to_id = self.repository.list_field_key_to_id(crf_template_id=crf_template_id)
        now: datetime = timezone.now()
        create_items: list[dict[str, object]] = []
        for item in normalized_reasons:
            field_template_id = self._resolve_field_template_id(
                canonical_field_key=item.field_key,
                field_key_to_id=field_key_to_id,
            )
            create_items.append(
                {
                    "field_template_id": field_template_id,
                    "reason": item.reason,
                    "resolution_note": (item.field_label or item.field_key),
                },
            )
        return self.repository.bulk_create_manual_open_queries(
            page_state_id=page_state_id,
            items=create_items,
            actor_user_id=actor_user_id,
            now=now,
        )

    def add_update_value_threads_for_changed_fields(
        self,
        *,
        page_state_id: int,
        crf_template_id: int,
        values_by_field_key: dict[str, object],
        actor_user_id: int | None,
    ) -> int:
        if not values_by_field_key:
            return 0

        field_key_to_id = self.repository.list_field_key_to_id(crf_template_id=crf_template_id)
        field_id_to_value: dict[int, object] = {}
        for raw_field_key, value in values_by_field_key.items():
            field_key = self._canonical_field_key(raw_field_key)
            field_template_id = self._resolve_field_template_id(
                canonical_field_key=field_key,
                field_key_to_id=field_key_to_id,
            )
            if field_template_id is None:
                continue
            field_id_to_value[field_template_id] = value

        query_ids_by_field_template = self.repository.list_latest_open_query_ids_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=tuple(field_id_to_value),
        )
        if not query_ids_by_field_template:
            return 0

        field_contexts = self.repository.list_field_thread_value_contexts(
            crf_template_id=crf_template_id,
            field_template_ids=tuple(query_ids_by_field_template),
        )
        now: datetime = timezone.now()
        created_count = 0
        for field_template_id, dataquery_id in query_ids_by_field_template.items():
            self.repository.create_query_thread_message(
                dataquery_id=dataquery_id,
                message_text=(
                    f"update value to "
                    f"{self._format_thread_value(field_id_to_value.get(field_template_id), field_contexts.get(field_template_id))}"
                ),
                message_type=_QUERY_THREAD_COMMENT,
                actor_user_id=actor_user_id,
                now=now,
                source=ReconcileQueryThreadSourceChoices.SYSTEM,
            )
            created_count += 1
        return created_count

    def open_query(
        self,
        *,
        page_state_id: int,
        field_template_id: int,
        message_text: str,
        actor_user_id: int | None,
    ) -> dict[str, object]:
        normalized_text = str(message_text or "").strip()
        if not normalized_text:
            raise ValueError("Message text is required.")
        if self.repository.has_open_query_for_page_field(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        ):
            raise ValueError("An open query already exists for this field.")
        now: datetime = timezone.now()
        dataquery = self.repository.create_manual_open_query(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            question_text=normalized_text,
            actor_user_id=actor_user_id,
            now=now,
        )
        thread = self.repository.create_query_thread_message(
            dataquery_id=dataquery.pk,
            message_text=normalized_text,
            message_type=_QUERY_THREAD_COMMENT,
            actor_user_id=actor_user_id,
            now=now,
        )
        return {
            "dataquery_id": dataquery.pk,
            "field_template_id": field_template_id,
            "message_text": thread.message_text,
            "message_type": thread.message_type,
            "created_at": (
                timezone.localtime(thread.created_at)
                if timezone.is_aware(thread.created_at)
                else thread.created_at
            ),
        }

    def reply_to_query(
        self,
        *,
        dataquery_id: int,
        page_state_id: int,
        field_template_id: int,
        message_text: str,
        actor_user_id: int | None,
    ) -> dict[str, object]:
        normalized_text = str(message_text or "").strip()
        if not normalized_text:
            raise ValueError("Message text is required.")
        if not self.repository.query_belongs_to_scope(
            dataquery_id=dataquery_id,
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        ):
            raise ValueError("Query does not belong to the current field.")
        now: datetime = timezone.now()
        thread = self.repository.create_query_thread_message(
            dataquery_id=dataquery_id,
            message_text=normalized_text,
            message_type=_QUERY_THREAD_COMMENT,
            actor_user_id=actor_user_id,
            now=now,
        )
        return {
            "dataquery_id": dataquery_id,
            "message_text": thread.message_text,
            "message_type": thread.message_type,
            "created_at": (
                timezone.localtime(thread.created_at)
                if timezone.is_aware(thread.created_at)
                else thread.created_at
            ),
            "closed": False,
        }

    def reply_and_close_query(
        self,
        *,
        dataquery_id: int,
        page_state_id: int,
        field_template_id: int,
        message_text: str,
        actor_user_id: int | None,
    ) -> dict[str, object]:
        normalized_text = str(message_text or "").strip()
        if not normalized_text:
            raise ValueError("Message text is required.")
        if not self.repository.query_belongs_to_scope(
            dataquery_id=dataquery_id,
            page_state_id=page_state_id,
            field_template_id=field_template_id,
        ):
            raise ValueError("Query does not belong to the current field.")
        now: datetime = timezone.now()
        thread = self.repository.create_query_thread_message(
            dataquery_id=dataquery_id,
            message_text=normalized_text,
            message_type=_QUERY_THREAD_RESOLUTION,
            actor_user_id=actor_user_id,
            now=now,
        )
        closed = self.repository.close_query(
            dataquery_id=dataquery_id,
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            resolution_note=normalized_text,
            actor_user_id=actor_user_id,
            now=now,
        )
        return {
            "dataquery_id": dataquery_id,
            "message_text": thread.message_text,
            "message_type": thread.message_type,
            "created_at": (
                timezone.localtime(thread.created_at)
                if timezone.is_aware(thread.created_at)
                else thread.created_at
            ),
            "closed": closed,
        }

    @classmethod
    def _format_thread_value(cls, value, field_context: dict[str, object] | None = None) -> str:
        if field_context and field_context.get("options"):
            label = cls._format_option_label_value(value, field_context.get("options"))
            if label:
                return label
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @classmethod
    def _format_option_label_value(cls, value, raw_options) -> str:
        label_by_value = cls._option_label_by_value(raw_options)
        if not label_by_value:
            return ""
        tokens = cls._value_tokens(value)
        labels = [label_by_value.get(token, token) for token in tokens]
        return ", ".join(label for label in labels if label)

    @classmethod
    def _option_label_by_value(cls, raw_options) -> dict[str, str]:
        static_options = cls._static_options(raw_options)
        label_by_value: dict[str, str] = {}
        for option in static_options:
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or "").strip()
            option_value = str(option.get("value") or label).strip()
            if option_value and label:
                label_by_value[option_value] = label
        return label_by_value

    @classmethod
    def _static_options(cls, raw_options):
        if not raw_options:
            return []
        parsed_options = raw_options
        if isinstance(raw_options, str):
            stripped_options = raw_options.strip()
            try:
                parsed_options = json.loads(stripped_options)
            except (TypeError, json.JSONDecodeError):
                parsed_options = stripped_options
        if isinstance(parsed_options, dict) and parsed_options.get("source") == "static":
            return parsed_options.get("static") or []
        return []

    @staticmethod
    def _value_tokens(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]
