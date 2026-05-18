from datetime import datetime

from apps.crf.models import CrfFieldTemplate
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
                    query_type=ReconcileDataQueryTypeChoices.MANUAL,
                    severity=ReconcileDataQuerySeverityChoices.MINOR,
                    is_blocking=True,
                    question_text=str(item.get("reason") or ""),
                    resolution_note=str(item.get("resolution_note") or "")[:1000],
                    opened_at=now,
                    closed_at=None,
                    page_state_id=page_state_id,
                    field_template_id=item.get("field_template_id"),
                    validation_rule_id=None,
                    data_version=item.get("data_version"),
                    field_path=item.get("field_path"),
                    assigned_to_id=None,
                    opened_by_id=actor_user_id,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                ),
            )
        if not records:
            return 0
        ReconcileDataQuery.objects.bulk_create(records)
        return len(records)

    @staticmethod
    def has_open_query_for_page_field(*, page_state_id: int, field_template_id: int) -> bool:
        return ReconcileDataQuery.objects.filter(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            status=ReconcileDataQueryStatusChoices.OPEN,
            deleted=False,
        ).exists()

    @staticmethod
    def create_manual_open_query(
        *,
        page_state_id: int,
        field_template_id: int,
        question_text: str,
        actor_user_id: int | None,
        now: datetime,
    ) -> ReconcileDataQuery:
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
            field_template_id=field_template_id,
            validation_rule_id=None,
            assigned_to_id=None,
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
    ) -> ReconcileQueryThread:
        return ReconcileQueryThread.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            message_text=message_text,
            message_type=message_type,
            visibility=ReconcileQueryThreadVisibilityChoices.SITE,
            source=ReconcileQueryThreadSourceChoices.MANUAL,
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
                status=ReconcileDataQueryStatusChoices.CLOSED,
                resolution_note=resolution_note[:1000],
                closed_at=now,
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


__all__ = ["DjangoReconcileDataQueryWriteRepository"]
