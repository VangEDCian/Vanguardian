from dataclasses import dataclass

from apps.datacapture.application.commands import (
    TriggerPageStateEventTransitionCommand,
)
from apps.datacapture.application.services.fact_evaluation import DataCaptureFactEvaluationService
from apps.datacapture.domain import DataCapturePageState
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
    fact_evaluation_service_class = DataCaptureFactEvaluationService
    subject_event_lifecycle_adapter_class = SubjectEventLifecycleAdapter

    def __init__(
        self,
        repository=None,
        fact_mapping_evaluator=None,
        fact_evaluation_service=None,
        subject_event_lifecycle_adapter=None,
    ):
        self.fact_evaluation_service = fact_evaluation_service or self.fact_evaluation_service_class(
            repository=repository,
            fact_mapping_evaluator=fact_mapping_evaluator,
        )
        self.subject_event_lifecycle_adapter = (
            subject_event_lifecycle_adapter or self.subject_event_lifecycle_adapter_class()
        )

    def execute(
        self,
        command: TriggerPageStateEventTransitionCommand,
    ) -> DataCaptureEventTransitionTriggerResult:
        page_state = self.fact_evaluation_service.get_page_state_or_raise(page_state_id=command.page_state_id)

        if not DataCapturePageState.is_event_transition_stable(page_state.status):
            return DataCaptureEventTransitionTriggerResult(
                page_state_id=page_state.id,
                status=page_state.status,
                facts=None,
                skipped_reason="page_state_not_stable",
            )

        evaluation = self.fact_evaluation_service.evaluate_for_event_instance(
            event_instance_id=page_state.visit_id,
        )
        transition_result = self.subject_event_lifecycle_adapter.trigger_event_transition(
            source_event_instance_id=page_state.visit_id,
            facts=evaluation.facts,
            actor_user_id=command.actor_user_id,
            trigger_source=command.trigger_source,
        )
        return DataCaptureEventTransitionTriggerResult(
            page_state_id=page_state.id,
            status=page_state.status,
            facts=evaluation.facts,
            transition_result=transition_result,
        )


__all__ = [
    "DataCaptureEventTransitionTriggerResult",
    "DataCapturePageStateEventTransitionService",
]
