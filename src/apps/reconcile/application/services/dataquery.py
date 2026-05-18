from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.reconcile.infrastructure.repositories import DjangoReconcileDataQueryWriteRepository

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
