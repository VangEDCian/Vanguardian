from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.commands import RecordEventGateEvaluationCommand
from apps.study.application.services.event_gate_evaluation import EventGateEvaluationRecorder


class EventGateEvaluationRecorderTests(SimpleTestCase):
    def test_record_persists_gate_evaluation_and_condition_results(self):
        repository = _EventGateEvaluationRepositoryStub()
        command = RecordEventGateEvaluationCommand(
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            event_instance_id=10,
            transition_rule_id=2,
            gate_code="transition_rule:2",
            gate_type="transition",
            target_action="open_event:101",
            result="fail",
            evaluated_by_id=99,
            rule_code="baseline_ok",
            rule_version="1.0",
            facts={"baseline_ok": False},
            failed_conditions=[{"reason_code": "condition_not_satisfied"}],
            blocking_reasons=["condition_not_satisfied"],
            source_context="datacapture",
            source_object_id=10,
            condition_results=[
                {
                    "fact_key": "baseline_ok",
                    "operator": "truthy",
                    "expected_value": "true",
                    "actual_value": "False",
                    "result": "fail",
                    "reason_code": "condition_not_satisfied",
                }
            ],
        )

        gate_evaluation = EventGateEvaluationRecorder(repository=repository).record(command)

        self.assertEqual(gate_evaluation.pk, 500)
        self.assertEqual(repository.created_gate_values["gate_code"], "transition_rule:2")
        self.assertEqual(repository.created_gate_values["result"], "fail")
        self.assertEqual(repository.created_gate_values["transition_rule_id"], 2)
        self.assertEqual(repository.created_gate_values["facts_json"], '{"baseline_ok": false}')
        self.assertEqual(repository.created_gate_values["blocking_reasons_json"], '["condition_not_satisfied"]')
        self.assertEqual(repository.condition_results[0]["fact_key"], "baseline_ok")


class _EventGateEvaluationRepositoryStub:
    def __init__(self):
        self.created_gate_values = None
        self.condition_results = []

    def now(self):
        return datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)

    def create_gate_evaluation(self, **values):
        self.created_gate_values = values
        return SimpleNamespace(pk=500)

    def bulk_create_gate_condition_results(self, *, gate_evaluation, conditions):
        self.condition_results = list(conditions)
        return self.condition_results
