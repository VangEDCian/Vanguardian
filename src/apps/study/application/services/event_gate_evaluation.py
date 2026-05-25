import json

from apps.study.application.commands import RecordEventGateEvaluationCommand
from apps.study.infrastructure.repositories import DjangoEventGateEvaluationRepository


class EventGateEvaluationRecorder:
    repository_class = DjangoEventGateEvaluationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def record(self, command: RecordEventGateEvaluationCommand):
        now = self.repository.now()
        gate_evaluation = self.repository.create_gate_evaluation(
            created_at=now,
            study_id=command.study_id,
            subject_id=command.subject_id,
            event_definition_id=command.event_definition_id,
            event_instance_id=command.event_instance_id,
            transition_rule_id=command.transition_rule_id,
            gate_code=command.gate_code,
            gate_type=command.gate_type,
            target_action=command.target_action,
            result=command.result,
            evaluated_at=now,
            evaluated_by_id=command.evaluated_by_id,
            rule_code=command.rule_code,
            rule_version=command.rule_version,
            facts_json=self._to_json(command.facts),
            failed_conditions_json=self._to_json(command.failed_conditions),
            blocking_reasons_json=self._to_json(command.blocking_reasons),
            source_context=command.source_context,
            source_object_id=command.source_object_id,
        )
        self.repository.bulk_create_gate_condition_results(
            gate_evaluation=gate_evaluation,
            conditions=command.condition_results,
        )
        return gate_evaluation

    @staticmethod
    def _to_json(value) -> str:
        return json.dumps(value or ([] if isinstance(value, list) else {}), ensure_ascii=True, sort_keys=True, default=str)


__all__ = ["EventGateEvaluationRecorder"]
