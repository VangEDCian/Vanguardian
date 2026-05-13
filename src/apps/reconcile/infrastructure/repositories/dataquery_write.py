from datetime import datetime

from apps.crf.models import CrfFieldTemplate
from apps.reconcile.models import (
    ReconcileDataQuery,
    ReconcileDataQuerySourceChoices,
    ReconcileDataQueryStatusChoices,
)


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
    def bulk_create_manual_open_queries(
        *,
        page_state_id: int,
        items: list[dict[str, object]],
        actor_user_id: int | None,
        now: datetime,
    ) -> int:
        records: list[ReconcileDataQuery] = []
        for item in items:
            records.append(
                ReconcileDataQuery(
                    created_at=now,
                    updated_at=now,
                    deleted=False,
                    status=ReconcileDataQueryStatusChoices.OPEN,
                    source=ReconcileDataQuerySourceChoices.MANUAL,
                    question_text=str(item.get("reason") or ""),
                    resolution_note=str(item.get("resolution_note") or "")[:255],
                    closed_at=None,
                    page_state_id=page_state_id,
                    field_template_id=item.get("field_template_id"),
                    validation_rule_id=None,
                    assigned_to_id=None,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                ),
            )
        if not records:
            return 0
        ReconcileDataQuery.objects.bulk_create(records)
        return len(records)


__all__ = ["DjangoReconcileDataQueryWriteRepository"]
