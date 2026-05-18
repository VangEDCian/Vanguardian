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
                condition_expression=None,
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
            SubjectEventTransitionService(repository=repository).execute(
                TriggerSubjectEventTransitionCommand(
                    source_event_instance_id=10,
                    actor_user_id=99,
                    trigger_source="datacapture",
                )
            )

        self.assertEqual(repository.created_planned_date, anchor_datetime + timedelta(days=5))


class _SubjectCommandRepositoryStub:
    def __init__(self, *, event_definitions, transition_rules):
        self.event_definitions = event_definitions
        self.transition_rules = transition_rules
        self.created_event_instances = []

    def list_enabled_event_definitions(self, *, study_id):
        return self.event_definitions

    def list_enabled_transition_rules(self, *, study_id, event_definition_ids):
        return self.transition_rules

    def build_event_instance(self, **kwargs):
        return SimpleNamespace(**kwargs)

    def bulk_create_event_instances(self, event_instances):
        self.created_event_instances = list(event_instances)


class _SubjectEventLifecycleRepositoryStub:
    def __init__(self, *, now):
        self._now = now
        self.created_planned_date = None

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
        return [
            StudyEventTransitionRuleSnapshot(
                id=1,
                from_event_definition_id=from_event_definition_id,
                to_event_definition_id=101,
                transition_type="sequential",
                condition_scope="subject_event",
                condition_code=None,
                condition_expression=None,
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
