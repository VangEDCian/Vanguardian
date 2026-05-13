from django.db.models import Count

from apps.reconcile.models import ReconcileDataQuery, ReconcileDataQueryStatusChoices


class DjangoReconcileDataQueryReadRepository:
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


__all__ = ["DjangoReconcileDataQueryReadRepository"]
