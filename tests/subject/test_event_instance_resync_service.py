from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.services.event_instance_resync import (
    SubjectEventInstanceResyncService,
)
from apps.subject.domain import SubjectEventInstance


class SubjectEventInstanceResyncServiceTests(SimpleTestCase):
    def test_resync_creates_missing_event_instances_for_existing_study_version_subjects(self):
        now = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=now,
            event_definitions=[
                _event_definition(pk=100, code="SCREENING"),
                _event_definition(pk=101, code="VISIT2"),
            ],
            transition_rules=[
                _transition_rule(
                    from_event_definition_id=100,
                    to_event_definition_id=101,
                    requires_previous_completion=True,
                    offset_days=7,
                )
            ],
            subject_ids=[20],
            existing_events_by_subject={
                20: {
                    100: _event_instance(
                        pk=10,
                        event_definition_id=100,
                        status=SubjectEventInstance.VERIFIED,
                    )
                }
            },
        )

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(repository=repository).resync_study_version(
                study_id=1,
                study_version="v1.0",
                actor_user_id=99,
            )

        self.assertEqual(result.created_count, 1)
        created_event = repository.created_events[0]
        self.assertEqual(created_event.subject_id, 20)
        self.assertEqual(created_event.event_definition_id, 101)
        self.assertEqual(created_event.status, SubjectEventInstance.OPEN)
        self.assertEqual(created_event.planned_date, now + timedelta(days=7))

    def test_resync_does_not_downgrade_already_open_event_instances(self):
        now = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        open_event = _event_instance(
            pk=11,
            event_definition_id=101,
            status=SubjectEventInstance.OPEN,
            event_name_snapshot="Old Visit 2",
        )
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=now,
            event_definitions=[
                _event_definition(pk=100, code="SCREENING"),
                _event_definition(pk=101, code="VISIT2", name="Visit 2 Updated"),
            ],
            transition_rules=[
                _transition_rule(
                    from_event_definition_id=100,
                    to_event_definition_id=101,
                    requires_previous_completion=True,
                )
            ],
            subject_ids=[20],
            existing_events_by_subject={
                20: {
                    100: _event_instance(
                        pk=10,
                        event_definition_id=100,
                        status=SubjectEventInstance.NOT_READY,
                    ),
                    101: open_event,
                }
            },
        )

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(repository=repository).resync_study_version(
                study_id=1,
                study_version="v1.0",
                actor_user_id=99,
            )

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.updated_count, 2)
        update = next(item for item in repository.updated_events if item["event_instance"].pk == 11)
        self.assertEqual(update["event_instance"].pk, 11)
        self.assertEqual(update["desired_status"], SubjectEventInstance.NOT_READY)
        self.assertFalse(update["allow_status_change"])

    def test_resync_skips_subjects_without_instances_for_version_by_default(self):
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
            event_definitions=[_event_definition(pk=100, code="SCREENING")],
            transition_rules=[],
            subject_ids=[],
            all_subject_ids=[20],
            existing_events_by_subject={},
        )

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(repository=repository).resync_study_version(
                study_id=1,
                study_version="v2.0",
                actor_user_id=99,
            )

        self.assertEqual(result.subject_count, 0)
        self.assertEqual(result.created_count, 0)

    def test_resync_can_include_all_subjects_for_manual_protocol_migration(self):
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
            event_definitions=[_event_definition(pk=100, code="SCREENING")],
            transition_rules=[],
            subject_ids=[],
            all_subject_ids=[20],
            existing_events_by_subject={},
        )

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(repository=repository).resync_study_version(
                study_id=1,
                study_version="v2.0",
                actor_user_id=99,
                include_all_subjects=True,
            )

        self.assertEqual(result.subject_count, 1)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(repository.created_events[0].event_definition_id, 100)

    def test_resync_subject_active_study_version_targets_only_selected_subject(self):
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
            event_definitions=[_event_definition(pk=100, code="SCREENING", study_version="v2.0")],
            transition_rules=[],
            subject_ids=[],
            all_subject_ids=[20, 21],
            active_study_version="v2.0",
            existing_events_by_subject={},
        )

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(repository=repository).resync_subject_active_study_version(
                study_id=1,
                subject_id=20,
                actor_user_id=99,
            )

        self.assertEqual(result.study_version, "v2.0")
        self.assertEqual(result.subject_count, 1)
        self.assertEqual(result.event_definition_count, 1)
        self.assertEqual(result.reason, "completed")
        self.assertEqual(result.created_count, 1)
        self.assertEqual([event.subject_id for event in repository.created_events], [20])

    def test_resync_triggers_downstream_transitions_for_transition_ready_events(self):
        repository = _SubjectEventInstanceResyncRepositoryStub(
            now=datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc),
            event_definitions=[
                _event_definition(pk=100, code="SCREENING"),
                _event_definition(pk=101, code="VISIT2"),
            ],
            transition_rules=[],
            subject_ids=[20],
            transition_ready_event_instance_ids_by_subject={20: [10]},
            existing_events_by_subject={
                20: {
                    100: _event_instance(
                        pk=10,
                        event_definition_id=100,
                        status=SubjectEventInstance.COMPLETED,
                    ),
                }
            },
        )
        transition_service = _SubjectEventTransitionServiceStub(applied_event_count=1)

        with patch(
            "apps.subject.application.services.event_instance_resync.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = SubjectEventInstanceResyncService(
                repository=repository,
                transition_service=transition_service,
            ).resync_study_version(
                study_id=1,
                study_version="v1.0",
                actor_user_id=99,
                trigger_source="subject_list_resync_stage",
            )

        self.assertEqual(result.lifecycle_trigger_count, 1)
        self.assertEqual(result.downstream_transition_count, 1)
        self.assertEqual(len(transition_service.commands), 1)
        command = transition_service.commands[0]
        self.assertEqual(command.source_event_instance_id, 10)
        self.assertEqual(command.actor_user_id, 99)
        self.assertEqual(command.trigger_source, "subject_list_resync_stage")


class _SubjectEventInstanceResyncRepositoryStub:
    def __init__(
        self,
        *,
        now,
        event_definitions,
        transition_rules,
        subject_ids,
        existing_events_by_subject,
        all_subject_ids=None,
        active_study_version="v1.0",
        transition_ready_event_instance_ids_by_subject=None,
    ):
        self._now = now
        self.event_definitions = event_definitions
        self.transition_rules = transition_rules
        self.subject_ids = subject_ids
        self.all_subject_ids = all_subject_ids or subject_ids
        self.active_study_version = active_study_version
        self.existing_events_by_subject = existing_events_by_subject
        self.transition_ready_event_instance_ids_by_subject = transition_ready_event_instance_ids_by_subject or {}
        self.created_events = []
        self.updated_events = []

    def now(self):
        return self._now

    def resolve_active_study_version(self, *, study_id):
        return self.active_study_version

    def list_enabled_event_definitions(self, *, study_id, study_version):
        return self.event_definitions

    def list_enabled_transition_rules(self, *, study_id, study_version, event_definition_ids):
        return self.transition_rules

    def list_subject_ids_for_study_version(self, *, study_id, study_version):
        return self.subject_ids

    def list_subject_ids_for_study(self, *, study_id, subject_ids=None):
        if subject_ids is not None:
            return [subject_id for subject_id in self.all_subject_ids if subject_id in subject_ids]
        return self.all_subject_ids

    def list_event_instances_for_subject_version_for_update(
        self,
        *,
        study_id,
        subject_id,
        study_version,
        event_definition_ids,
    ):
        return self.existing_events_by_subject.get(subject_id, {})

    def list_transition_ready_event_instance_ids(self, *, study_id, subject_id, study_version):
        return self.transition_ready_event_instance_ids_by_subject.get(subject_id, [])

    def create_event_instance(
        self,
        *,
        subject_id,
        study_id,
        event_definition,
        status,
        planned_date,
        actor_user_id,
        now,
        trigger_source,
    ):
        event_instance = SimpleNamespace(
            subject_id=subject_id,
            study_id=study_id,
            event_definition_id=event_definition.pk,
            status=status,
            planned_date=planned_date or (now if status == SubjectEventInstance.OPEN else None),
        )
        self.created_events.append(event_instance)
        return event_instance

    def resync_event_instance(
        self,
        *,
        event_instance,
        event_definition,
        desired_status,
        planned_date,
        actor_user_id,
        now,
        trigger_source,
        allow_status_change,
    ):
        self.updated_events.append(
            {
                "event_instance": event_instance,
                "event_definition": event_definition,
                "desired_status": desired_status,
                "allow_status_change": allow_status_change,
            }
        )
        return event_instance.event_name_snapshot != event_definition.name or allow_status_change


class _SubjectEventTransitionServiceStub:
    def __init__(self, *, applied_event_count=0):
        self.applied_event_count = applied_event_count
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        return SimpleNamespace(applied_events=tuple(object() for _ in range(self.applied_event_count)))


def _event_definition(*, pk, code, name=None, study_version="v1.0"):
    return SimpleNamespace(
        pk=pk,
        study_version=study_version,
        code=code,
        name=name or code.title(),
        event_type="visit_based",
    )


def _transition_rule(
    *,
    from_event_definition_id,
    to_event_definition_id,
    requires_previous_completion,
    offset_days=None,
    auto_open=True,
    condition_code=None,
):
    return SimpleNamespace(
        from_event_definition_id=from_event_definition_id,
        to_event_definition_id=to_event_definition_id,
        requires_previous_completion=requires_previous_completion,
        offset_days=offset_days,
        auto_open=auto_open,
        condition_code=condition_code,
        condition_definition=None,
    )


def _event_instance(*, pk, event_definition_id, status, event_name_snapshot=None):
    return SimpleNamespace(
        pk=pk,
        id=pk,
        event_definition_id=event_definition_id,
        status=status,
        planned_date=None,
        event_code_snapshot="",
        event_name_snapshot=event_name_snapshot or "",
        event_type_snapshot="visit_based",
    )
