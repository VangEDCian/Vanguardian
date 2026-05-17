from dataclasses import dataclass

from apps.datacapture.application.commands import (
    DataCapturePageStateNotFoundError,
    TriggerPageStateEventTransitionCommand,
)
from apps.datacapture.domain import DataCaptureFactMappingEvaluator, DataCapturePageState
from apps.datacapture.infrastructure.repositories import DjangoDataCaptureFactMappingRepository
from apps.subject.public import SubjectEventLifecycleAdapter


@dataclass(frozen=True)
class DataCaptureEventTransitionTriggerResult:
    page_state_id: int
    status: str | None
    facts: dict[str, bool] | None
    transition_result: object | None = None
    skipped_reason: str | None = None

    @property
    def has_changes(self) -> bool:
        return bool(getattr(self.transition_result, "has_changes", False))


class DataCapturePageStateEventTransitionService:
    repository_class = DjangoDataCaptureFactMappingRepository
    fact_mapping_evaluator_class = DataCaptureFactMappingEvaluator
    subject_event_lifecycle_adapter_class = SubjectEventLifecycleAdapter

    def __init__(
        self,
        repository=None,
        fact_mapping_evaluator=None,
        subject_event_lifecycle_adapter=None,
    ):
        self.repository = repository or self.repository_class()
        self.fact_mapping_evaluator = fact_mapping_evaluator or self.fact_mapping_evaluator_class()
        self.subject_event_lifecycle_adapter = (
            subject_event_lifecycle_adapter or self.subject_event_lifecycle_adapter_class()
        )

    def execute(
        self,
        command: TriggerPageStateEventTransitionCommand,
    ) -> DataCaptureEventTransitionTriggerResult:
        page_state = self.repository.get_page_state_for_event_transition(
            page_state_id=command.page_state_id,
        )
        if page_state is None:
            raise DataCapturePageStateNotFoundError(command.page_state_id)

        if not DataCapturePageState.is_event_transition_stable(page_state.status):
            return DataCaptureEventTransitionTriggerResult(
                page_state_id=page_state.id,
                status=page_state.status,
                facts=None,
                skipped_reason="page_state_not_stable",
            )

        mappings = self.repository.list_enabled_fact_mappings(
            study_id=page_state.study_id,
            study_version=page_state.study_version,
            crf_template_id=page_state.crf_template_id,
            event_definition_id=page_state.event_definition_id,
        )
        facts = self.fact_mapping_evaluator.build_facts(
            final_data=page_state.final_data,
            mappings=mappings,
        )
        transition_result = self.subject_event_lifecycle_adapter.trigger_event_transition(
            source_event_instance_id=page_state.visit_id,
            facts=facts or {},
            actor_user_id=command.actor_user_id,
            trigger_source=command.trigger_source,
        )
        return DataCaptureEventTransitionTriggerResult(
            page_state_id=page_state.id,
            status=page_state.status,
            facts=facts or {},
            transition_result=transition_result,
        )


__all__ = [
    "DataCaptureEventTransitionTriggerResult",
    "DataCapturePageStateEventTransitionService",
]
