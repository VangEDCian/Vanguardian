from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.reconcile.infrastructure.repositories import DjangoReconcileDataQueryWriteRepository

_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")


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
