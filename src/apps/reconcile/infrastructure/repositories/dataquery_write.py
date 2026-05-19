from datetime import datetime

from django.utils.translation import get_language

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
