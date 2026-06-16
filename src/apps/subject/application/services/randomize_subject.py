from dataclasses import dataclass

from django.db import transaction

from apps.audit.public import AuditContextAdapter
from apps.study.public import assign_randomization_slot_for_subject
from apps.subject.infrastructure.repositories.randomization import (
    DjangoSubjectRandomizationRepository,
)


class RandomizeSubjectError(RuntimeError):
    """Raised when RandomizeSubject cannot complete."""


class RandomizeSubjectGateError(RandomizeSubjectError):
    """Raised when subject is not eligible for randomization workflow."""


@dataclass(frozen=True)
class RandomizeSubjectCommand:
    subject_id: int
    actor_id: int | None = None
    event_instance_id: int | None = None
    event_definition_id: int | None = None
    scheme_id: int | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    source: str = "system"
    stratum_code: str | None = None


@dataclass(frozen=True)
class RandomizationSummary:
    subject_id: int
    study_id: int
    site_id: int
    scheme_id: int | None
    scheme_code: str
    arm_id: int | None
    arm_code: str
    arm_name: str
    slot_id: int | None
    sequence_no: int | None
    randomization_event_id: int | None
    randomization_status: str
    randomization_datetime: object
    randomization_number: str
    randomization_source: str
    period_count: int


@dataclass(frozen=True)
class SubjectRandomized:
    subject_id: int
    study_id: int
    site_id: int
    randomization_event_id: int | None
    scheme_id: int | None
    arm_id: int | None
    slot_id: int | None


class RandomizeSubject:
    repository_class = DjangoSubjectRandomizationRepository
    audit_adapter_class = AuditContextAdapter
    slot_assigner = staticmethod(assign_randomization_slot_for_subject)

    def __init__(
        self,
        *,
        repository=None,
        audit_adapter=None,
        slot_assigner=None,
        event_publisher=None,
    ):
        self.repository = repository or self.repository_class()
        self.audit_adapter = audit_adapter or self.audit_adapter_class()
        self.slot_assigner = slot_assigner or self.__class__.slot_assigner
        self.event_publisher = event_publisher or (lambda event: None)

    def execute(self, command: RandomizeSubjectCommand) -> RandomizationSummary | None:
        subject = self.repository.get_subject_scope(subject_id=command.subject_id)
        if subject is None:
            raise RandomizeSubjectGateError("Subject was not found for randomization.")

        existing = self.repository.get_existing_randomization_summary(
            subject_id=command.subject_id,
            summary_class=RandomizationSummary,
        )
        if existing and existing.slot_id:
            self.repository.ensure_subject_periods(
                subject_id=command.subject_id,
                arm_id=existing.arm_id,
                actor_user_id=command.actor_id,
                now=self.repository.now(),
            )
            return existing

        if not self.repository.is_subject_enrolled_or_allowed_to_randomize(
            study_id=subject.study_id,
            subject_id=subject.pk,
        ):
            raise RandomizeSubjectGateError("Subject is not enrolled or otherwise allowed to randomize.")

        with transaction.atomic():
            now = self.repository.now()
            assignment = self.slot_assigner(
                study_id=subject.study_id,
                subject_id=subject.pk,
                event_instance_id=command.event_instance_id,
                actor_user_id=command.actor_id,
                scheme_id=command.scheme_id,
                stratum_code=command.stratum_code,
            )
            if assignment is None:
                return None

            summary = self.repository.record_assignment(
                subject=subject,
                assignment=assignment,
                event_instance_id=command.event_instance_id,
                actor_user_id=command.actor_id,
                source=command.source,
                reason_code=command.reason_code,
                reason_text=command.reason_text,
                now=now,
                summary_class=RandomizationSummary,
            )
            self.audit_adapter.record_event(
                action="subject.randomized",
                object_type="study_subject_randomization",
                object_id=str(subject.pk),
                before_data={},
                after_data={
                    "subject_id": summary.subject_id,
                    "scheme_id": summary.scheme_id,
                    "arm_id": summary.arm_id,
                    "slot_id": summary.slot_id,
                    "randomization_event_id": summary.randomization_event_id,
                },
                actor_user_id=command.actor_id,
            )

            transaction.on_commit(
                lambda: self.event_publisher(
                    SubjectRandomized(
                        subject_id=summary.subject_id,
                        study_id=summary.study_id,
                        site_id=summary.site_id,
                        randomization_event_id=summary.randomization_event_id,
                        scheme_id=summary.scheme_id,
                        arm_id=summary.arm_id,
                        slot_id=summary.slot_id,
                    )
                )
            )
            return summary


__all__ = [
    "RandomizationSummary",
    "RandomizeSubject",
    "RandomizeSubjectCommand",
    "RandomizeSubjectError",
    "RandomizeSubjectGateError",
    "SubjectRandomized",
]
