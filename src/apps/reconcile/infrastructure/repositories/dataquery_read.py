from django.db.models import Count

from apps.reconcile.models import ReconcileDataQuery, ReconcileDataQueryStatusChoices


class DjangoReconcileDataQueryReadRepository:
    @staticmethod
    def _active_status_excludes() -> tuple[str, ...]:
        return (
            ReconcileDataQueryStatusChoices.CLOSED,
            ReconcileDataQueryStatusChoices.CANCELLED,
        )

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
                field_template_id__isnull=False,
                field_template_id__in=field_template_ids,
            )
            .exclude(status__in=self._active_status_excludes())
            .values("field_template_id")
            .annotate(query_count=Count("id"))
        )
        return {int(row["field_template_id"]): int(row["query_count"]) for row in rows}

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


__all__ = ["DjangoReconcileDataQueryReadRepository"]
