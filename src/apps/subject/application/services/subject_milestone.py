from dataclasses import dataclass

from django.utils import timezone

from apps.audit.public import AuditContextAdapter
from apps.shared.application import ApplicationValidationError
from apps.subject.infrastructure.repositories.subject_milestone import (
    DjangoSubjectMilestoneRepository,
)


class SubjectMilestoneCorrectionError(ApplicationValidationError):
    default_message = "Subject milestone correction failed."


@dataclass(frozen=True)
class CorrectSubjectMilestoneCommand:
    milestone_id: int
    actor_id: int
    reason: str
    occurred_at: object | None = None
    occurred_date: object | None = None
    occurred_time: object | None = None
    date_precision: str | None = None
    status: str = "corrected"


class CorrectSubjectMilestone:
    audit_adapter_class = AuditContextAdapter
    repository_class = DjangoSubjectMilestoneRepository

    def __init__(self, *, audit_adapter=None, repository=None):
        self.audit_adapter = audit_adapter or self.audit_adapter_class()
        self.repository = repository or self.repository_class()

    def execute(self, command: CorrectSubjectMilestoneCommand):
        if not command.reason or not str(command.reason).strip():
            raise SubjectMilestoneCorrectionError("Correction reason is required.")
        milestone = self.repository.get_current_milestone(milestone_id=command.milestone_id)
        before_data = self._snapshot(milestone)
        now = timezone.now()
        milestone = self.repository.save_correction(
            milestone=milestone,
            occurred_at=command.occurred_at,
            occurred_date=command.occurred_date,
            occurred_time=command.occurred_time,
            date_precision=command.date_precision,
            status=command.status,
            reason=command.reason,
            actor_id=command.actor_id,
            now=now,
        )
        after_data = self._snapshot(milestone)
        self.audit_adapter.record_event(
            action="subject_milestone.corrected",
            object_type="study_subject_milestone",
            object_id=str(milestone.pk),
            before_data=before_data,
            after_data=after_data,
            actor_user_id=command.actor_id,
        )
        return milestone

    @staticmethod
    def _snapshot(milestone):
        return {
            "id": milestone.pk,
            "subject_id": milestone.subject_id,
            "milestone_code": milestone.milestone_code,
            "occurred_at": milestone.occurred_at,
            "occurred_date": milestone.occurred_date,
            "occurred_time": milestone.occurred_time,
            "date_precision": milestone.date_precision,
            "status": milestone.status,
            "correction_reason": milestone.correction_reason,
        }


__all__ = [
    "CorrectSubjectMilestone",
    "CorrectSubjectMilestoneCommand",
    "SubjectMilestoneCorrectionError",
]
