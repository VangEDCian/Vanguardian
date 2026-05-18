from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.choices import EventInstanceStatusChoices
from apps.subject.infrastructure.repositories.subject_commands import DjangoSubjectCommandRepository


class SubjectCommandRepositoryInitialEventLogTests(SimpleTestCase):
    def test_bulk_create_event_instances_creates_initial_transition_logs(self):
        now = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        initial_event_instance = SimpleNamespace(
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            repeat_index=1,
            status=EventInstanceStatusChoices.OPEN,
            created_at=now,
            created_by_id=99,
        )
        persisted_event_instance = SimpleNamespace(
            pk=55,
            study_id=1,
            subject_id=20,
            event_definition_id=100,
            repeat_index=1,
            status=EventInstanceStatusChoices.OPEN,
        )

        with (
            patch(
                "apps.subject.infrastructure.repositories.subject_commands."
                "SubjectEventInstance.objects.bulk_create"
            ) as event_bulk_create,
            patch(
                "apps.subject.infrastructure.repositories.subject_commands."
                "SubjectEventInstance.objects.filter"
            ) as event_filter,
            patch(
                "apps.subject.infrastructure.repositories.subject_commands."
                "SubjectEventInstanceTransitionLog.objects.bulk_create"
            ) as log_bulk_create,
        ):
            event_filter.return_value.only.return_value = [persisted_event_instance]

            DjangoSubjectCommandRepository().bulk_create_event_instances(
                [initial_event_instance]
            )

        event_bulk_create.assert_called_once_with([initial_event_instance])
        event_filter.assert_called_once_with(
            subject_id__in={20},
            event_definition_id__in={100},
            repeat_index__in={1},
            deleted=False,
        )
        log_bulk_create.assert_called_once()
        transition_logs = log_bulk_create.call_args.args[0]
        self.assertEqual(len(transition_logs), 1)
        transition_log = transition_logs[0]
        self.assertEqual(transition_log.study_id, 1)
        self.assertEqual(transition_log.subject_id, 20)
        self.assertEqual(transition_log.source_event_instance_id, 55)
        self.assertIsNone(transition_log.target_event_instance_id)
        self.assertIsNone(transition_log.transition_rule_id)
        self.assertEqual(transition_log.from_event_definition_id, 100)
        self.assertIsNone(transition_log.to_event_definition_id)
        self.assertEqual(transition_log.from_status, "not_created")
        self.assertEqual(transition_log.to_status, EventInstanceStatusChoices.OPEN)
        self.assertEqual(transition_log.trigger_source, "subject_created")
        self.assertEqual(transition_log.result, "applied")
        self.assertEqual(transition_log.reason, "initial_event_instance_created")
        self.assertEqual(transition_log.facts_json, "{}")
        self.assertEqual(transition_log.created_at, now)
        self.assertEqual(transition_log.updated_at, now)
        self.assertEqual(transition_log.created_by_id, 99)
        self.assertEqual(transition_log.updated_by_id, 99)
