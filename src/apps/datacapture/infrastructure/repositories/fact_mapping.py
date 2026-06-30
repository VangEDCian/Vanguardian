from django.db.models import Count, Q

from apps.datacapture.infrastructure.models.capture import (
    DataCaptureEventFactContext,
    DataCaptureFactForm,
    DataCaptureFactMappingRule,
    DataCaptureFactSource,
    DataCapturePageStateSnapshot,
)
from apps.datacapture.models import DataCaptureFactMapping, DataCapturePageState
from apps.reconcile.models import ReconcileDataQuery, ReconcileDataQueryStatusChoices


class DjangoDataCaptureFactMappingRepository:
    def get_fact_mapping_for_import(
        self,
        *,
        study_id: int,
        study_version: str,
        event_definition_id: int,
        crf_template_id: int,
        fact_key: str,
    ):
        return (
            DataCaptureFactMapping.objects.filter(
                study_id=study_id,
                study_version=study_version,
                event_definition_id=event_definition_id,
                crf_template_id=crf_template_id,
                fact_key=fact_key,
            )
            .order_by("deleted", "id")
            .first()
        )

    def create_fact_mapping(self, **values):
        return DataCaptureFactMapping.objects.create(**values)

    def save_fact_mapping(self, fact_mapping, *, update_fields):
        fact_mapping.save(update_fields=update_fields)
        return fact_mapping

    def get_page_state_for_event_transition(
        self,
        *,
        page_state_id: int,
    ) -> DataCapturePageStateSnapshot | None:
        page_state = (
            DataCapturePageState.objects.select_related("visit")
            .filter(pk=page_state_id, deleted=False)
            .only(
                "id",
                "status",
                "final_data",
                "data_version",
                "current_entry_id",
                "crf_template_id",
                "subject_id",
                "visit_id",
                "visit__study_id",
                "visit__study_version",
                "visit__event_definition_id",
            )
            .first()
        )
        if page_state is None:
            return None

        visit = page_state.visit
        return DataCapturePageStateSnapshot(
            id=page_state.pk,
            status=page_state.status,
            final_data=page_state.final_data,
            data_version=page_state.data_version,
            current_entry_id=page_state.current_entry_id,
            crf_template_id=page_state.crf_template_id,
            subject_id=page_state.subject_id,
            visit_id=page_state.visit_id,
            study_id=visit.study_id,
            study_version=visit.study_version,
            event_definition_id=visit.event_definition_id,
        )

    def get_fact_source_for_event_transition(
        self,
        *,
        page_state_id: int,
    ) -> DataCaptureFactSource | None:
        current_page_state = (
            DataCapturePageState.objects.select_related("crf_template", "current_entry")
            .filter(pk=page_state_id, deleted=False)
            .only(
                "id",
                "subject_id",
                "visit_id",
                "crf_template_id",
                "crf_template__code",
                "final_data",
                "current_entry_id",
                "current_entry__data",
            )
            .first()
        )
        if current_page_state is None:
            return None

        page_states = list(
            DataCapturePageState.objects.select_related("crf_template")
            .filter(
                subject_id=current_page_state.subject_id,
                visit_id=current_page_state.visit_id,
                deleted=False,
            )
            .only(
                "id",
                "status",
                "final_data",
                "crf_template_id",
                "crf_template__code",
            )
            .order_by("crf_template__code", "id")
        )
        open_query_counts = self._count_open_queries_by_page_state_ids(
            page_state_ids=[page_state.pk for page_state in page_states],
        )
        return self._build_fact_source_from_page_states(
            page_states=page_states,
            current_page_state_id=current_page_state.pk,
            open_query_counts_by_page_state_id=open_query_counts,
        )

    def get_event_fact_context_for_event_transition(
        self,
        *,
        event_instance_id: int,
    ) -> DataCaptureEventFactContext | None:
        page_states = list(
            DataCapturePageState.objects.select_related("crf_template", "visit")
            .filter(
                visit_id=event_instance_id,
                deleted=False,
            )
            .only(
                "id",
                "status",
                "final_data",
                "crf_template_id",
                "crf_template__code",
                "visit_id",
                "visit__study_id",
                "visit__study_version",
                "visit__event_definition_id",
            )
            .order_by("crf_template__code", "id")
        )
        if not page_states:
            return None

        open_query_counts = self._count_open_queries_by_page_state_ids(
            page_state_ids=[page_state.pk for page_state in page_states],
        )
        crf_template_ids = tuple(
            dict.fromkeys(int(page_state.crf_template_id) for page_state in page_states)
        )
        visit = page_states[0].visit
        return DataCaptureEventFactContext(
            event_instance_id=event_instance_id,
            study_id=visit.study_id,
            study_version=visit.study_version,
            event_definition_id=visit.event_definition_id,
            crf_template_ids=crf_template_ids,
            fact_source=self._build_fact_source_from_page_states(
                page_states=page_states,
                current_page_state_id=None,
                open_query_counts_by_page_state_id=open_query_counts,
            ),
        )

    def list_enabled_fact_mappings(
        self,
        *,
        study_id: int,
        study_version: str,
        crf_template_id: int,
        event_definition_id: int,
    ) -> list[DataCaptureFactMappingRule]:
        mappings = (
            DataCaptureFactMapping.objects.filter(
                study_id=study_id,
                study_version=study_version,
                crf_template_id=crf_template_id,
                deleted=False,
                is_enabled=True,
            )
            .filter(Q(event_definition_id=event_definition_id) | Q(event_definition_id__isnull=True))
            .only(
                "id",
                "field_code",
                "source_path",
                "fact_key",
                "operator",
                "expected_value",
                "value_type",
                "default_value",
                "display_order",
            )
            .order_by("display_order", "id")
        )
        return [self._to_fact_mapping_rule(mapping) for mapping in mappings]

    def list_enabled_fact_mappings_for_event(
        self,
        *,
        study_id: int,
        study_version: str,
        event_definition_id: int,
        crf_template_ids: tuple[int, ...],
    ) -> list[DataCaptureFactMappingRule]:
        if not crf_template_ids:
            return []
        mappings = (
            DataCaptureFactMapping.objects.filter(
                study_id=study_id,
                study_version=study_version,
                crf_template_id__in=crf_template_ids,
                deleted=False,
                is_enabled=True,
            )
            .filter(Q(event_definition_id=event_definition_id) | Q(event_definition_id__isnull=True))
            .only(
                "id",
                "field_code",
                "source_path",
                "fact_key",
                "operator",
                "expected_value",
                "value_type",
                "default_value",
                "display_order",
            )
            .order_by("display_order", "id")
        )
        return [self._to_fact_mapping_rule(mapping) for mapping in mappings]

    @staticmethod
    def _to_fact_mapping_rule(mapping) -> DataCaptureFactMappingRule:
        return DataCaptureFactMappingRule(
            id=mapping.pk,
            field_code=mapping.field_code,
            source_path=mapping.source_path,
            fact_key=mapping.fact_key,
            operator=mapping.operator,
            expected_value=mapping.expected_value,
            value_type=mapping.value_type,
            default_value=mapping.default_value,
        )

    @staticmethod
    def _count_open_queries_by_page_state_ids(*, page_state_ids: list[int]) -> dict[int, int]:
        if not page_state_ids:
            return {}
        rows = (
            ReconcileDataQuery.objects.filter(
                page_state_id__in=page_state_ids,
                deleted=False,
                status=ReconcileDataQueryStatusChoices.OPEN,
            )
            .values("page_state_id")
            .annotate(open_query_count=Count("id"))
        )
        return {int(row["page_state_id"]): int(row["open_query_count"]) for row in rows}

    @staticmethod
    def _build_fact_source_from_page_states(
        *,
        page_states: list,
        current_page_state_id: int | None,
        open_query_counts_by_page_state_id: dict[int, int],
    ) -> DataCaptureFactSource:
        forms: dict[str, DataCaptureFactForm] = {}
        current_form_code: str | None = None
        for page_state in page_states:
            form_code = str(getattr(getattr(page_state, "crf_template", None), "code", "") or "").strip()
            if not form_code:
                form_code = f"CRF_{int(page_state.crf_template_id)}"
            final_data = getattr(page_state, "final_data", "")
            current_entry = getattr(page_state, "current_entry", None)
            current_entry_data = getattr(current_entry, "data", "") if current_entry is not None else ""
            raw_data = (
                final_data
                if str(final_data or "").strip()
                else current_entry_data
            )
            forms[form_code] = DataCaptureFactForm.from_raw(
                data=raw_data,
                status=page_state.status,
                open_queries=open_query_counts_by_page_state_id.get(int(page_state.pk), 0),
            )
            if current_page_state_id is not None and int(page_state.pk) == int(current_page_state_id):
                current_form_code = form_code
        return DataCaptureFactSource(forms=forms, current_form_code=current_form_code)


__all__ = ["DjangoDataCaptureFactMappingRepository"]
