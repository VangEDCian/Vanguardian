from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.application.services.randomize_subject import (
    RandomizationSummary,
    RandomizeSubject,
    RandomizeSubjectCommand,
)


class RandomizeSubjectTests(SimpleTestCase):
    def test_assigns_available_slot_and_records_randomization_summary(self):
        repository = _RandomizeRepositoryStub()
        slot_assigner = _SlotAssignerStub(arm_code="SEQ_E_N", sequence_no=1)
        audit = _AuditStub()
        published_events = []

        with (
            patch("apps.subject.application.services.randomize_subject.transaction.atomic", return_value=nullcontext()),
            patch("apps.subject.application.services.randomize_subject.transaction.on_commit", side_effect=lambda fn: fn()),
        ):
            summary = RandomizeSubject(
                repository=repository,
                slot_assigner=slot_assigner,
                audit_adapter=audit,
                event_publisher=published_events.append,
            ).execute(
                RandomizeSubjectCommand(
                    subject_id=20,
                    event_instance_id=30,
                    actor_id=99,
                    source="workflow_action",
                )
            )

        self.assertEqual(summary.slot_id, 5)
        self.assertEqual(summary.arm_code, "SEQ_E_N")
        self.assertEqual(summary.randomization_number, "1")
        self.assertEqual(repository.recorded_assignments[0]["assignment"].slot_id, 5)
        self.assertEqual(repository.period_materializations, [])
        self.assertEqual(audit.events[0]["action"], "subject.randomized")
        self.assertEqual(published_events[0].slot_id, 5)

    def test_is_idempotent_for_existing_randomized_subject(self):
        existing = RandomizationSummary(
            subject_id=20,
            study_id=1,
            site_id=2,
            scheme_id=10,
            scheme_code="NNG31_XOVER",
            arm_id=11,
            arm_code="SEQ_E_N",
            arm_name="Eprex -> NANOKINE",
            slot_id=5,
            sequence_no=1,
            randomization_event_id=None,
            randomization_status="assigned",
            randomization_datetime=datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc),
            randomization_number="1",
            randomization_source="workflow_action",
            period_count=2,
        )
        repository = _RandomizeRepositoryStub(existing=existing)
        slot_assigner = _SlotAssignerStub()

        summary = RandomizeSubject(
            repository=repository,
            slot_assigner=slot_assigner,
            audit_adapter=_AuditStub(),
        ).execute(RandomizeSubjectCommand(subject_id=20, actor_id=99))

        self.assertEqual(summary.slot_id, 5)
        self.assertEqual(slot_assigner.calls, [])
        self.assertEqual(repository.period_materializations[0]["arm_id"], 11)

    def test_materializes_sequence_arm_periods_for_seq_e_n(self):
        repository = _RandomizeRepositoryStub(period_count_by_arm={11: 2})
        slot_assigner = _SlotAssignerStub(arm_id=11, arm_code="SEQ_E_N")

        with (
            patch("apps.subject.application.services.randomize_subject.transaction.atomic", return_value=nullcontext()),
            patch("apps.subject.application.services.randomize_subject.transaction.on_commit", side_effect=lambda fn: fn()),
        ):
            summary = RandomizeSubject(
                repository=repository,
                slot_assigner=slot_assigner,
                audit_adapter=_AuditStub(),
            ).execute(RandomizeSubjectCommand(subject_id=20, actor_id=99))

        self.assertEqual(summary.arm_code, "SEQ_E_N")
        self.assertEqual(summary.period_count, 2)

    def test_materializes_sequence_arm_periods_for_seq_n_e(self):
        repository = _RandomizeRepositoryStub(period_count_by_arm={12: 2})
        slot_assigner = _SlotAssignerStub(arm_id=12, arm_code="SEQ_N_E")

        with (
            patch("apps.subject.application.services.randomize_subject.transaction.atomic", return_value=nullcontext()),
            patch("apps.subject.application.services.randomize_subject.transaction.on_commit", side_effect=lambda fn: fn()),
        ):
            summary = RandomizeSubject(
                repository=repository,
                slot_assigner=slot_assigner,
                audit_adapter=_AuditStub(),
            ).execute(RandomizeSubjectCommand(subject_id=20, actor_id=99))

        self.assertEqual(summary.arm_code, "SEQ_N_E")
        self.assertEqual(summary.period_count, 2)


class _RandomizeRepositoryStub:
    def __init__(self, *, existing=None, period_count_by_arm=None):
        self.subject = SimpleNamespace(pk=20, study_id=1, site_id=2)
        self.existing = existing
        self.period_count_by_arm = period_count_by_arm or {11: 2, 12: 2}
        self.recorded_assignments = []
        self.period_materializations = []

    def now(self):
        return datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)

    def get_subject_scope(self, *, subject_id):
        return self.subject if subject_id == self.subject.pk else None

    def get_existing_randomization_summary(self, *, subject_id, summary_class):
        return self.existing

    def ensure_subject_periods(self, **kwargs):
        self.period_materializations.append(kwargs)
        return self.period_count_by_arm.get(kwargs["arm_id"], 0)

    def is_subject_enrolled_or_allowed_to_randomize(self, *, study_id, subject_id):
        return True

    def record_assignment(self, **kwargs):
        self.recorded_assignments.append(kwargs)
        assignment = kwargs["assignment"]
        period_count = self.period_count_by_arm.get(assignment.arm_id, 0)
        return kwargs["summary_class"](
            subject_id=kwargs["subject"].pk,
            study_id=kwargs["subject"].study_id,
            site_id=kwargs["subject"].site_id,
            scheme_id=assignment.scheme_id,
            scheme_code=assignment.scheme_code,
            arm_id=assignment.arm_id,
            arm_code=assignment.arm_code,
            arm_name=assignment.arm_name,
            slot_id=assignment.slot_id,
            sequence_no=assignment.sequence_no,
            randomization_event_id=1000,
            randomization_status="assigned",
            randomization_datetime=kwargs["now"],
            randomization_number=str(assignment.sequence_no),
            randomization_source=kwargs["source"],
            period_count=period_count,
        )


class _SlotAssignerStub:
    def __init__(self, *, arm_id=11, arm_code="SEQ_E_N", sequence_no=1):
        self.calls = []
        self.arm_id = arm_id
        self.arm_code = arm_code
        self.sequence_no = sequence_no

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            slot_id=5,
            scheme_id=10,
            scheme_code="NNG31_XOVER",
            arm_id=self.arm_id,
            arm_code=self.arm_code,
            arm_name="Sequence arm",
            sequence_no=self.sequence_no,
        )


class _AuditStub:
    def __init__(self):
        self.events = []

    def record_event(self, **kwargs):
        self.events.append(kwargs)
