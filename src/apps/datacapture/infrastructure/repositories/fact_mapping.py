from django.db.models import Q

from apps.datacapture.domain import (
    DataCaptureFactMappingRule,
    DataCapturePageStateSnapshot,
)
from apps.datacapture.models import DataCaptureFactMapping, DataCapturePageState


class DjangoDataCaptureFactMappingRepository:
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
            crf_template_id=page_state.crf_template_id,
            subject_id=page_state.subject_id,
            visit_id=page_state.visit_id,
            study_id=visit.study_id,
            study_version=visit.study_version,
            event_definition_id=visit.event_definition_id,
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


__all__ = ["DjangoDataCaptureFactMappingRepository"]
