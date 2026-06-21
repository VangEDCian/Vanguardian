from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.commands import RecordEventGateEvaluationCommand
from apps.study.application.services.event_gate_evaluation import (
    EventGateEvaluationHistoryReader,
    EventGateEvaluationRecorder,
)


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

    def test_history_reader_normalizes_gate_evaluation_rows(self):
        reader = EventGateEvaluationHistoryReader(repository=_EventGateEvaluationHistoryRepositoryStub())

        records = reader.list_for_subject(study_id=1, subject_id=20, limit=25, search="nguyen", field_name="ready")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["category"], "event_gate")
        self.assertEqual(records[0]["field_name"], "baseline_ready")
        self.assertEqual(records[0]["field_description"], "Baseline / open_event / baseline_rule")
        self.assertEqual(records[0]["value"], "fail")
        self.assertEqual(records[0]["user_display"], "System")
        self.assertEqual(records[0]["scope"], "Baseline")
        self.assertEqual(records[0]["action"], "Open Event")
        self.assertEqual(records[0]["to_value"], "Fail")
        self.assertEqual(records[0]["reason"], "Missing Baseline Facts")
        self.assertIn({"label": "Gate Code", "value": "baseline_ready"}, records[0]["details"])
        self.assertEqual(reader.repository.kwargs["search"], "nguyen")
        self.assertEqual(reader.repository.kwargs["field_name"], "ready")


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


class _EventGateEvaluationHistoryRepositoryStub:
    def __init__(self):
        self.kwargs = None

    def list_gate_evaluation_history_for_subject(self, *, study_id, subject_id, limit, search="", field_name=""):
        self.kwargs = {"search": search, "field_name": field_name}
        return [
            SimpleNamespace(
                evaluated_at=datetime(2026, 6, 4, 9, 0, tzinfo=timezone.utc),
                audit_field_name="baseline_ready",
                audit_field_description="Baseline / open_event / baseline_rule",
                audit_value="fail",
                audit_user_display="System",
                event_definition=SimpleNamespace(name="Baseline", code="BASELINE"),
                target_action="open_event",
                gate_type="transition",
                result="fail",
                evaluated_by_id=None,
                blocking_reasons_json='["missing_baseline_facts"]',
                failed_conditions_json="[]",
                audit_condition_results=[
                    SimpleNamespace(result="fail"),
                ],
                gate_code="baseline_ready",
                rule_code="baseline_rule",
                rule_version="1",
                source_context="datacapture",
            )
        ]
