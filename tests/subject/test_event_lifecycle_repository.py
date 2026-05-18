from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.core.choices import EventInstanceStatusChoices
from apps.subject.infrastructure.repositories.event_lifecycle import (
    DjangoSubjectEventLifecycleRepository,
)


class SubjectEventLifecycleRepositoryTransitionLogTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.repository = DjangoSubjectEventLifecycleRepository()
        self.event_instance = SimpleNamespace(
            pk=11,
            study_id=1,
            subject_id=21,
            event_definition_id=31,
        )
        self.repository.record_transition_log = Mock()

    def test_open_event_instance_records_status_transition_log(self):
        self.event_instance.status = EventInstanceStatusChoices.PLANNED
        self.repository._get_event_instance_model_for_status_update = Mock(
            return_value=self.event_instance
        )
        self.repository.get_event_instance_for_update = Mock(return_value="snapshot")

        with patch(
            "apps.subject.infrastructure.repositories.event_lifecycle."
            "SubjectEventInstance.objects.filter"
        ) as filter_mock:
            result = self.repository.open_event_instance(
                event_instance_id=11,
                actor_user_id=6,
                now=self.now,
            )

        self.assertEqual(result, "snapshot")
        filter_mock.assert_called_once_with(pk=11)
        filter_mock.return_value.update.assert_called_once()
        self.repository.record_transition_log.assert_called_once_with(
            study_id=1,
            subject_id=21,
            source_event_instance_id=11,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=31,
            to_event_definition_id=None,
            from_status=EventInstanceStatusChoices.PLANNED,
            to_status=EventInstanceStatusChoices.OPEN,
            trigger_source="subject_event_open",
            result="applied",
            reason="event_opened",
            facts={},
            actor_user_id=6,
            now=self.now,
        )

    def test_complete_event_instance_records_status_transition_log(self):
        self.event_instance.status = EventInstanceStatusChoices.OPEN
        self.repository._get_event_instance_model_for_status_update = Mock(
            return_value=self.event_instance
        )

        with patch(
            "apps.subject.infrastructure.repositories.event_lifecycle."
            "SubjectEventInstance.objects.filter"
        ) as filter_mock:
            result = self.repository.complete_event_instance(
                event_instance_id=11,
                actor_user_id=7,
                now=self.now,
            )

        self.assertIs(result, True)
        filter_mock.assert_called_once_with(pk=11)
        filter_mock.return_value.update.assert_called_once()
        self.repository.record_transition_log.assert_called_once_with(
            study_id=1,
            subject_id=21,
            source_event_instance_id=11,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=31,
            to_event_definition_id=None,
            from_status=EventInstanceStatusChoices.OPEN,
            to_status=EventInstanceStatusChoices.COMPLETED,
            trigger_source="datacapture_submit",
            result="applied",
            reason="all_visit_forms_submitted",
            facts={},
            actor_user_id=7,
            now=self.now,
        )

    def test_verify_event_instance_records_status_transition_log(self):
        self.event_instance.status = EventInstanceStatusChoices.COMPLETED
        self.repository._get_event_instance_model_for_status_update = Mock(
            return_value=self.event_instance
        )

        with patch(
            "apps.subject.infrastructure.repositories.event_lifecycle."
            "SubjectEventInstance.objects.filter"
        ):
            result = self.repository.verify_event_instance(
                event_instance_id=11,
                actor_user_id=8,
                now=self.now,
            )

        self.assertIs(result, True)
        self.repository.record_transition_log.assert_called_once_with(
            study_id=1,
            subject_id=21,
            source_event_instance_id=11,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=31,
            to_event_definition_id=None,
            from_status=EventInstanceStatusChoices.COMPLETED,
            to_status=EventInstanceStatusChoices.VERIFIED,
            trigger_source="verification",
            result="applied",
            reason="all_visit_forms_verified",
            facts={},
            actor_user_id=8,
            now=self.now,
        )

    def test_mark_event_instance_in_progress_records_status_transition_log(self):
        self.event_instance.status = EventInstanceStatusChoices.VERIFIED
        self.repository._get_event_instance_model_for_status_update = Mock(
            return_value=self.event_instance
        )

        with patch(
            "apps.subject.infrastructure.repositories.event_lifecycle."
            "SubjectEventInstance.objects.filter"
        ):
            result = self.repository.mark_event_instance_in_progress(
                event_instance_id=11,
                actor_user_id=9,
                now=self.now,
            )

        self.assertIs(result, True)
        self.repository.record_transition_log.assert_called_once_with(
            study_id=1,
            subject_id=21,
            source_event_instance_id=11,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=31,
            to_event_definition_id=None,
            from_status=EventInstanceStatusChoices.VERIFIED,
            to_status=EventInstanceStatusChoices.IN_PROGRESS,
            trigger_source="reopen_form",
            result="applied",
            reason="correction_required",
            facts={},
            actor_user_id=9,
            now=self.now,
        )

    def test_noop_status_change_does_not_record_transition_log(self):
        self.repository._get_event_instance_model_for_status_update = Mock(return_value=None)

        result = self.repository.complete_event_instance(
            event_instance_id=11,
            actor_user_id=7,
            now=self.now,
        )

        self.assertIs(result, False)
        self.repository.record_transition_log.assert_not_called()
