from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.crf.models import CrfFieldTemplate
from apps.reconcile.models import (
    ReconcileDataQuery,
    ReconcileDataQuerySourceChoices,
    ReconcileDataQueryStatusChoices,
)

_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")


@dataclass(frozen=True)
class ReconcileChangeReasonItem:
    field_key: str
    field_label: str
    reason: str


class ReconcileDataQueryWriteService:
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

        field_key_to_id = dict(
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                deleted=False,
            ).values_list("field_key", "id")
        )
        now: datetime = timezone.now()
        records: list[ReconcileDataQuery] = []
        for item in normalized_reasons:
            field_template_id = self._resolve_field_template_id(
                canonical_field_key=item.field_key,
                field_key_to_id=field_key_to_id,
            )
            records.append(
                ReconcileDataQuery(
                    created_at=now,
                    updated_at=now,
                    deleted=False,
                    status=ReconcileDataQueryStatusChoices.OPEN,
                    source=ReconcileDataQuerySourceChoices.MANUAL,
                    question_text=item.reason,
                    resolution_note=(item.field_label or item.field_key)[:255],
                    closed_at=None,
                    page_state_id=page_state_id,
                    field_template_id=field_template_id,
                    validation_rule_id=None,
                    assigned_to_id=None,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                )
            )

        ReconcileDataQuery.objects.bulk_create(records)
        return len(records)

