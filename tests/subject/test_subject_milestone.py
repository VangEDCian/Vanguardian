from datetime import datetime, timezone

from django.test import SimpleTestCase

from apps.subject.application.services.subject_milestone import (
    CorrectSubjectMilestone,
    CorrectSubjectMilestoneCommand,
    SubjectMilestoneCorrectionError,
)


class CorrectSubjectMilestoneTests(SimpleTestCase):
    def test_requires_reason(self):
        with self.assertRaises(SubjectMilestoneCorrectionError):
            CorrectSubjectMilestone(audit_adapter=_AuditStub()).execute(
                CorrectSubjectMilestoneCommand(
                    milestone_id=1,
                    actor_id=99,
                    reason="",
                )
            )

    def test_updates_source_time_and_writes_audit_without_mutating_system_timestamps(self):
        milestone = _Milestone()
        repository = _MilestoneRepositoryStub(milestone)
        corrected_at = datetime(2026, 5, 20, 8, 30, tzinfo=timezone.utc)
        audit = _AuditStub()

        CorrectSubjectMilestone(audit_adapter=audit, repository=repository).execute(
            CorrectSubjectMilestoneCommand(
                milestone_id=1,
                actor_id=99,
                reason="source correction",
                occurred_at=corrected_at,
                status="corrected",
            )
        )

        self.assertEqual(milestone.occurred_at, corrected_at)
        self.assertEqual(milestone.status, "corrected")
        self.assertEqual(milestone.correction_reason, "source correction")
        self.assertIn("updated_at", milestone.saved_update_fields)
        self.assertNotIn("created_at", milestone.saved_update_fields)
        self.assertEqual(audit.events[0]["action"], "subject_milestone.corrected")


class _Milestone:
    pk = 1
    subject_id = 20
    milestone_code = "ICF_SIGNED"
    occurred_at = None
    occurred_date = None
    occurred_time = None
    date_precision = None
    status = "confirmed"
    correction_reason = None

    def save(self, *, update_fields):
        self.saved_update_fields = update_fields


class _AuditStub:
    def __init__(self):
        self.events = []

    def record_event(self, **kwargs):
        self.events.append(kwargs)


class _MilestoneRepositoryStub:
    def __init__(self, milestone):
        self.milestone = milestone

    def get_current_milestone(self, *, milestone_id):
        return self.milestone

    def save_correction(
        self,
        *,
        milestone,
        occurred_at,
        occurred_date,
        occurred_time,
        date_precision,
        status,
        reason,
        actor_id,
        now,
    ):
        milestone.occurred_at = occurred_at
        milestone.occurred_date = occurred_date
        milestone.occurred_time = occurred_time
        milestone.date_precision = date_precision
        milestone.status = status
        milestone.correction_reason = reason
        milestone.updated_at = now
        milestone.updated_by_id = actor_id
        milestone.save(
            update_fields=[
                "occurred_at",
                "occurred_date",
                "occurred_time",
                "date_precision",
                "status",
                "correction_reason",
                "updated_at",
                "updated_by_id",
            ]
        )
        return milestone
