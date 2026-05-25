from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.commands import TriggerSubjectEventTransitionCommand
from apps.subject.application.services.create_subject import CreateSubjectService
from apps.subject.application.services.event_lifecycle import SubjectEventTransitionService
from apps.subject.domain import (
    StudyEventDefinitionSnapshot,
    StudyEventTransitionRuleSnapshot,
    SubjectEventInstanceSnapshot,
)


class CreateSubjectEventInstanceScheduleTests(SimpleTestCase):
    def test_initializes_open_root_event_schedule_at_subject_creation_time(self):
        anchor_datetime = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        event_definitions = [
            self._event_definition(pk=100, code="SCREENING"),
            self._event_definition(pk=101, code="VISIT_2"),
        ]
        transition_rules = [
            SimpleNamespace(
                from_event_definition_id=100,
                to_event_definition_id=101,
                requires_previous_completion=True,
                condition_code=None,
                condition_definition=None,
                offset_days=3,
            )
        ]
        repository = _SubjectCommandRepositoryStub(
            event_definitions=event_definitions,
            transition_rules=transition_rules,
        )
        subject = SimpleNamespace(pk=20, study_id=1)

        CreateSubjectService(repository=repository)._initialize_subject_event_instances(
            subject=subject,
            actor_user_id=99,
            now=anchor_datetime,
        )

        event_instances_by_definition = {
            event_instance.event_definition_id: event_instance
            for event_instance in repository.created_event_instances
        }
        self.assertEqual(event_instances_by_definition[100].planned_date, anchor_datetime)
        self.assertEqual(event_instances_by_definition[100].opened_at, anchor_datetime)
        self.assertEqual(event_instances_by_definition[100].opened_by_id, 99)
        self.assertEqual(
            event_instances_by_definition[101].planned_date,
            anchor_datetime + timedelta(days=3),
        )
        self.assertIsNone(event_instances_by_definition[101].opened_at)
        self.assertIsNone(event_instances_by_definition[101].opened_by_id)

    def test_initial_open_events_trigger_workflow_actions(self):
        anchor_datetime = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        repository = _SubjectCommandRepositoryStub(
            event_definitions=[self._event_definition(pk=100, code="RANDOMIZATION")],
            transition_rules=[],
            open_event_instance_ids=[55],
        )
        workflow_action_service = _WorkflowActionServiceStub()
        subject = SimpleNamespace(pk=20, study_id=1)

        CreateSubjectService(
            repository=repository,
            workflow_action_service=workflow_action_service,
        )._initialize_subject_event_instances(
            subject=subject,
            actor_user_id=99,
            now=anchor_datetime,
        )

        self.assertEqual(workflow_action_service.open_event_ids, [55])

    def test_initializes_event_instances_for_active_study_version_only(self):
        anchor_datetime = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        repository = _SubjectCommandRepositoryStub(
            event_definitions=[self._event_definition(pk=100, code="SCREENING")],
            transition_rules=[],
            active_study_version="v2.0",
        )
        subject = SimpleNamespace(pk=20, study_id=1)

        CreateSubjectService(repository=repository)._initialize_subject_event_instances(
            subject=subject,
            actor_user_id=99,
            now=anchor_datetime,
        )

        self.assertEqual(repository.requested_event_definition_version, "v2.0")
        self.assertEqual(repository.requested_transition_rule_version, "v2.0")

    @staticmethod
    def _event_definition(*, pk, code):
        return SimpleNamespace(
            pk=pk,
            study_version="1.0",
            code=code,
            name=code.title(),
            event_type="visit_based",
        )


class SubjectEventTransitionScheduleTests(SimpleTestCase):
    def test_auto_created_target_event_uses_rule_offset_days_as_planned_date(self):
        anchor_datetime = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        repository = _SubjectEventLifecycleRepositoryStub(now=anchor_datetime)

        with patch("apps.subject.application.services.event_lifecycle.transaction.atomic", return_value=nullcontext()):
            workflow_action_service = _WorkflowActionServiceStub()
            gate_evaluation_recorder = _GateEvaluationRecorderStub()
            SubjectEventTransitionService(
                repository=repository,
                workflow_action_service=workflow_action_service,
                gate_evaluation_recorder=gate_evaluation_recorder,
            ).execute(
                TriggerSubjectEventTransitionCommand(
                    source_event_instance_id=10,
                    actor_user_id=99,
                    trigger_source="datacapture",
                )
            )

        self.assertEqual(repository.created_planned_date, anchor_datetime + timedelta(days=5))
        self.assertEqual(workflow_action_service.open_event_ids, [11])
        self.assertEqual(len(gate_evaluation_recorder.commands), 1)
        gate_command = gate_evaluation_recorder.commands[0]
        self.assertEqual(gate_command.gate_code, "transition_rule:1")
        self.assertEqual(gate_command.gate_type, "transition")
        self.assertEqual(gate_command.result, "pass")
        self.assertEqual(gate_command.transition_rule_id, 1)
        self.assertEqual(gate_command.target_action, "open_event:101")
        self.assertEqual(len(gate_command.condition_results), 1)
        self.assertEqual(gate_command.condition_results[0]["fact_key"], "transition_rule:1")
        self.assertEqual(gate_command.condition_results[0]["operator"], "evaluate_rule")
        self.assertEqual(gate_command.condition_results[0]["result"], "pass")

    def test_failed_transition_rule_is_recorded_as_gate_evaluation(self):
        repository = _SubjectEventLifecycleRepositoryStub(
            now=datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc),
            transition_rule=StudyEventTransitionRuleSnapshot(
                id=2,
                from_event_definition_id=100,
                to_event_definition_id=101,
                transition_type="conditional",
                condition_scope="subject_event",
                condition_code="baseline_ok",
                condition_definition_id=None,
                auto_open=True,
                auto_create=False,
                requires_previous_completion=True,
                allow_skip=False,
                display_order=1,
            ),
        )
        gate_evaluation_recorder = _GateEvaluationRecorderStub()

        with patch("apps.subject.application.services.event_lifecycle.transaction.atomic", return_value=nullcontext()):
            result = SubjectEventTransitionService(
                repository=repository,
                workflow_action_service=_WorkflowActionServiceStub(),
                gate_evaluation_recorder=gate_evaluation_recorder,
            ).execute(
                TriggerSubjectEventTransitionCommand(
                    source_event_instance_id=10,
                    facts={"baseline_ok": False},
                    actor_user_id=99,
                    trigger_source="datacapture",
                )
            )

        self.assertFalse(result.has_changes)
        self.assertEqual(len(gate_evaluation_recorder.commands), 1)
        gate_command = gate_evaluation_recorder.commands[0]
        self.assertEqual(gate_command.gate_code, "transition_rule:2")
        self.assertEqual(gate_command.result, "fail")
        self.assertEqual(gate_command.transition_rule_id, 2)
        self.assertEqual(gate_command.blocking_reasons, ["condition_not_satisfied"])
        self.assertEqual(gate_command.failed_conditions[0]["reason_code"], "condition_not_satisfied")
        self.assertEqual(len(gate_command.condition_results), 2)
        self.assertEqual(gate_command.condition_results[0]["fact_key"], "baseline_ok")
        self.assertEqual(gate_command.condition_results[0]["result"], "fail")
        self.assertEqual(gate_command.condition_results[1]["operator"], "evaluate_rule")
        self.assertEqual(gate_command.condition_results[1]["actual_value"], "condition_not_satisfied")


class _SubjectCommandRepositoryStub:
    def __init__(self, *, event_definitions, transition_rules, open_event_instance_ids=(), active_study_version="1.0"):
        self.event_definitions = event_definitions
        self.transition_rules = transition_rules
        self.created_event_instances = []
        self.open_event_instance_ids = list(open_event_instance_ids)
        self.active_study_version = active_study_version
        self.requested_event_definition_version = None
        self.requested_transition_rule_version = None

    def resolve_active_study_version(self, *, study_id):
        return self.active_study_version

    def list_enabled_event_definitions(self, *, study_id, study_version=None):
        self.requested_event_definition_version = study_version
        return self.event_definitions

    def list_enabled_transition_rules(self, *, study_id, event_definition_ids, study_version=None):
        self.requested_transition_rule_version = study_version
        return self.transition_rules

    def build_event_instance(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def bulk_create_event_instances(self, event_instances):
        self.created_event_instances = list(event_instances)

    def list_open_event_instance_ids_for_subject(self, *, subject_id):
        return list(self.open_event_instance_ids)


class _WorkflowActionServiceStub:
    def __init__(self):
        self.open_event_ids = []

    def execute_for_open_event(self, *, event_instance_id, actor_user_id):
        self.open_event_ids.append(event_instance_id)


class _GateEvaluationRecorderStub:
    def __init__(self):
        self.commands = []

    def record(self, command):
        self.commands.append(command)
        return command


class _SubjectEventLifecycleRepositoryStub:
    def __init__(self, *, now, transition_rule=None):
        self._now = now
        self.created_planned_date = None
        self.transition_rule = transition_rule

    def now(self):
        return self._now

    def get_event_instance_for_update(self, *, event_instance_id):
        return SubjectEventInstanceSnapshot(
            id=event_instance_id,
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            study_version="1.0",
            repeat_index=1,
            status="verified",
            event_code="SCREENING",
            event_name="Screening",
            event_type="visit_based",
        )

    def list_enabled_transition_rules_from(self, *, study_id, study_version, from_event_definition_id):
        if self.transition_rule is not None:
            return [self.transition_rule]
        return [
            StudyEventTransitionRuleSnapshot(
                id=1,
                from_event_definition_id=from_event_definition_id,
                to_event_definition_id=101,
                transition_type="sequential",
                condition_scope="subject_event",
                condition_code=None,
                condition_definition_id=None,
                auto_open=True,
                auto_create=True,
                requires_previous_completion=True,
                allow_skip=False,
                display_order=1,
                offset_days=5,
            )
        ]

    def list_event_instances_for_update(self, *, subject_id, event_definition_ids):
        return {}

    def get_event_definition(self, *, event_definition_id):
        return StudyEventDefinitionSnapshot(
            id=event_definition_id,
            study_id=1,
            study_version="1.0",
            code="VISIT_2",
            name="Visit 2",
            event_type="visit_based",
        )

    def create_open_event_instance(self, *, planned_date=None, **kwargs):
        self.created_planned_date = planned_date
        return SubjectEventInstanceSnapshot(
            id=11,
            study_id=1,
            subject_id=20,
            event_definition_id=101,
            study_version="1.0",
            repeat_index=1,
            status="open",
            event_code="VISIT_2",
            event_name="Visit 2",
            event_type="visit_based",
        )

    def record_transition_log(self, **kwargs):
        return None
