from django.db.models import Count
from django.db.models.functions import Coalesce

from apps.reconcile.models import ReconcileDataQuery, ReconcileDataQueryStatusChoices, ReconcileQueryThread


class DjangoReconcileDataQueryReadRepository:
    @staticmethod
    def _active_status_excludes() -> tuple[str, ...]:
        return ("cancelled", "closed")

    def count_open_queries_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, int]:
        if not field_template_ids:
            return {}
        rows = (
            ReconcileDataQuery.objects.filter(
                page_state_id=page_state_id,
                deleted=False,
                status=ReconcileDataQueryStatusChoices.OPEN,
                field_template_id__isnull=False,
                field_template_id__in=field_template_ids,
            )
            .values("field_template_id")
            .annotate(query_count=Count("id"))
        )
        return {int(row["field_template_id"]): int(row["query_count"]) for row in rows}

    def has_open_query_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return ReconcileDataQuery.objects.filter(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            deleted=False,
            status=ReconcileDataQueryStatusChoices.OPEN,
        ).exists()

    def has_active_blocking_query_for_page_field(self, *, page_state_id: int, field_template_id: int) -> bool:
        return (
            ReconcileDataQuery.objects.filter(
                page_state_id=page_state_id,
                field_template_id=field_template_id,
                deleted=False,
                is_blocking=True,
            )
            .exclude(status__in=self._active_status_excludes())
            .exists()
        )

    def has_active_blocking_query_for_page(self, *, page_state_id: int) -> bool:
        return (
            ReconcileDataQuery.objects.filter(
                page_state_id=page_state_id,
                deleted=False,
                is_blocking=True,
            )
            .exclude(status__in=self._active_status_excludes())
            .exists()
        )

    def list_latest_query_messages_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        limit_per_field: int = 10,
    ) -> dict[int, list[dict[str, object]]]:
        if not field_template_ids:
            return {}
        open_query_ids_by_field = self.list_latest_active_query_ids_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )
        field_id_by_query_id = {query_id: field_id for field_id, query_id in open_query_ids_by_field.items()}
        if not field_id_by_query_id:
            return {}
        rows = (
            ReconcileQueryThread.objects.filter(
                dataquery_id__in=tuple(field_id_by_query_id),
                deleted=False,
            )
            .order_by("dataquery_id", "-created_at", "-id")
            .values(
                "dataquery_id",
                "message_text",
                "message_type",
                "created_at",
                "author_id",
            )
        )
        grouped: dict[int, list[dict[str, object]]] = {}
        for row in rows:
            field_template_id = field_id_by_query_id[int(row["dataquery_id"])]
            bucket = grouped.setdefault(field_template_id, [])
            if len(bucket) >= limit_per_field:
                continue
            bucket.append(
                {
                    "dataquery_id": row["dataquery_id"],
                    "text": row["message_text"],
                    "status": row["message_type"],
                    "created_at": row["created_at"],
                    "opened_by_id": row["author_id"],
                },
            )
        return grouped

    def list_latest_active_query_ids_by_page_state_and_field_templates(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
    ) -> dict[int, int]:
        if not field_template_ids:
            return {}
        rows = (
            ReconcileDataQuery.objects.filter(
                page_state_id=page_state_id,
                deleted=False,
                status=ReconcileDataQueryStatusChoices.OPEN,
                field_template_id__isnull=False,
                field_template_id__in=field_template_ids,
            )
            .annotate(sort_at=Coalesce("opened_at", "created_at"))
            .order_by("field_template_id", "-sort_at", "-id")
            .values("field_template_id", "id")
        )
        out: dict[int, int] = {}
        for row in rows:
            field_template_id = int(row["field_template_id"])
            out.setdefault(field_template_id, int(row["id"]))
        return out

    def count_query_threads_since_current_user_last_comment(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        current_user_id: int | None,
    ) -> dict[int, int]:
        if not field_template_ids or current_user_id is None:
            return {}
        open_query_ids_by_field = self.list_latest_active_query_ids_by_page_state_and_field_templates(
            page_state_id=page_state_id,
            field_template_ids=field_template_ids,
        )
        field_id_by_query_id = {query_id: field_id for field_id, query_id in open_query_ids_by_field.items()}
        if not field_id_by_query_id:
            return {}
        rows = (
            ReconcileQueryThread.objects.filter(
                dataquery_id__in=tuple(field_id_by_query_id),
                deleted=False,
            )
            .order_by("dataquery_id", "created_at", "id")
            .values("dataquery_id", "created_at", "author_id", "created_by_id")
        )
        latest_current_user_comment_by_query: dict[int, object] = {}
        buffered_rows = list(rows)
        for row in buffered_rows:
            if row["author_id"] == current_user_id or row["created_by_id"] == current_user_id:
                latest_current_user_comment_by_query[int(row["dataquery_id"])] = row["created_at"]

        counts: dict[int, int] = {}
        for row in buffered_rows:
            dataquery_id = int(row["dataquery_id"])
            last_current_user_comment_at = latest_current_user_comment_by_query.get(dataquery_id)
            is_current_user_comment = row["author_id"] == current_user_id or row["created_by_id"] == current_user_id
            if is_current_user_comment:
                continue
            if last_current_user_comment_at is not None and row["created_at"] <= last_current_user_comment_at:
                continue
            field_template_id = field_id_by_query_id[dataquery_id]
            counts[field_template_id] = counts.get(field_template_id, 0) + 1
        return counts


__all__ = ["DjangoReconcileDataQueryReadRepository"]
