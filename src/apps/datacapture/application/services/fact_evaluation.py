from dataclasses import dataclass
from typing import Any

from apps.datacapture.application.commands import DataCapturePageStateNotFoundError
from apps.datacapture.domain import DataCaptureFactMappingEvaluator
from apps.datacapture.infrastructure.repositories import DjangoDataCaptureFactMappingRepository


@dataclass(frozen=True)
class DataCaptureFactEvaluation:
    page_state: object
    facts: dict[str, bool]
    fact_source: object | None

    @property
    def source_data_for_hash(self) -> Any:
        if self.fact_source is not None:
            return self.fact_source.to_jsonpath_context()
        return self.page_state.final_data


@dataclass(frozen=True)
class DataCaptureEventFactEvaluation:
    event_instance_id: int
    facts: dict[str, bool]
    fact_source: object | None

    @property
    def source_data_for_hash(self) -> Any:
        if self.fact_source is not None:
            return self.fact_source.to_jsonpath_context()
        return None


class DataCaptureFactEvaluationService:
    repository_class = DjangoDataCaptureFactMappingRepository
    fact_mapping_evaluator_class = DataCaptureFactMappingEvaluator

    def __init__(self, repository=None, fact_mapping_evaluator=None):
        self.repository = repository or self.repository_class()
        self.fact_mapping_evaluator = fact_mapping_evaluator or self.fact_mapping_evaluator_class()

    def get_page_state_or_raise(self, *, page_state_id: int):
        page_state = self.repository.get_page_state_for_event_transition(page_state_id=page_state_id)
        if page_state is None:
            raise DataCapturePageStateNotFoundError(page_state_id)
        return page_state

    def evaluate_for_page_state(self, *, page_state_id: int) -> DataCaptureFactEvaluation:
        page_state = self.get_page_state_or_raise(page_state_id=page_state_id)
        return self.evaluate(page_state=page_state)

    def evaluate(self, *, page_state) -> DataCaptureFactEvaluation:
        mappings = self.repository.list_enabled_fact_mappings(
            study_id=page_state.study_id,
            study_version=page_state.study_version,
            crf_template_id=page_state.crf_template_id,
            event_definition_id=page_state.event_definition_id,
        )
        fact_source = self.repository.get_fact_source_for_event_transition(page_state_id=page_state.id)
        facts = self.fact_mapping_evaluator.build_facts(
            final_data=page_state.final_data,
            mappings=mappings,
            fact_source=fact_source,
        ) or {}
        return DataCaptureFactEvaluation(
            page_state=page_state,
            facts=facts,
            fact_source=fact_source,
        )

    def evaluate_for_event_instance(self, *, event_instance_id: int) -> DataCaptureEventFactEvaluation:
        context = self.repository.get_event_fact_context_for_event_transition(
            event_instance_id=event_instance_id,
        )
        if context is None:
            return DataCaptureEventFactEvaluation(
                event_instance_id=event_instance_id,
                facts={},
                fact_source=None,
            )

        mappings = self.repository.list_enabled_fact_mappings_for_event(
            study_id=context.study_id,
            study_version=context.study_version,
            event_definition_id=context.event_definition_id,
            crf_template_ids=context.crf_template_ids,
        )
        facts = self.fact_mapping_evaluator.build_facts(
            mappings=mappings,
            fact_source=context.fact_source,
        ) or {}
        return DataCaptureEventFactEvaluation(
            event_instance_id=event_instance_id,
            facts=facts,
            fact_source=context.fact_source,
        )


__all__ = [
    "DataCaptureEventFactEvaluation",
    "DataCaptureFactEvaluation",
    "DataCaptureFactEvaluationService",
]
