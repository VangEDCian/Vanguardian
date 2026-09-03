from dataclasses import dataclass

from django.db import transaction

from apps.audit.public import AuditContextAdapter
from apps.study.domain import SubjectIdentifierPolicyError
from apps.study.public import (
    assign_randomization_slot_for_subject,
    get_subject_identifier_policy,
)
from apps.subject.application.services.period_lifecycle import (
    SubjectPeriodLifecycleService,
)
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
    period_lifecycle_service_class = SubjectPeriodLifecycleService
    slot_assigner = staticmethod(assign_randomization_slot_for_subject)

    def __init__(
        self,
        *,
        repository=None,
        audit_adapter=None,
        slot_assigner=None,
        event_publisher=None,
        period_lifecycle_service=None,
        identifier_policy_reader=None,
    ):
        self.repository = repository or self.repository_class()
        self.audit_adapter = audit_adapter or self.audit_adapter_class()
        self.slot_assigner = slot_assigner or self.__class__.slot_assigner
        self.event_publisher = event_publisher or (lambda event: None)
        self.period_lifecycle_service = (
            period_lifecycle_service or self.period_lifecycle_service_class()
        )
        self.identifier_policy_reader = identifier_policy_reader or get_subject_identifier_policy

    def execute(self, command: RandomizeSubjectCommand) -> RandomizationSummary | None:
        subject = self.repository.get_subject_scope(subject_id=command.subject_id)
        if subject is None:
            raise RandomizeSubjectGateError("Subject was not found for randomization.")

        existing = self.repository.get_existing_randomization_summary(
            subject_id=command.subject_id,
            summary_class=RandomizationSummary,
        )
        if existing and existing.slot_id:
            with transaction.atomic():
                now = self.repository.now()
                subject = self.repository.get_subject_for_identifier_assignment(
                    subject_id=command.subject_id
                )
                identifier_change = self._apply_subject_identifier_policy(
                    subject=subject,
                    randomization_code=existing.randomization_number,
                    actor_user_id=command.actor_id,
                    now=now,
                )
                self._record_identifier_change(
                    subject=subject,
                    identifier_change=identifier_change,
                    randomization_event_id=existing.randomization_event_id,
                    actor_user_id=command.actor_id,
                    occurred_at=now,
                )
                self.repository.ensure_subject_periods(
                    subject_id=command.subject_id,
                    arm_id=existing.arm_id,
                    subject_code=subject.subject_code,
                    actor_user_id=command.actor_id,
                    now=now,
                )
                self.period_lifecycle_service.initialize_after_randomization(
                    subject_id=command.subject_id,
                    actor_user_id=command.actor_id,
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

            subject = self.repository.get_subject_for_identifier_assignment(
                subject_id=command.subject_id
            )
            randomization_code = str(
                getattr(assignment, "randomization_code", None)
                or assignment.sequence_no
            )
            identifier_change = self._apply_subject_identifier_policy(
                subject=subject,
                randomization_code=randomization_code,
                actor_user_id=command.actor_id,
                now=now,
            )

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
            self._record_identifier_change(
                subject=subject,
                identifier_change=identifier_change,
                randomization_event_id=summary.randomization_event_id,
                actor_user_id=command.actor_id,
                occurred_at=now,
            )
            self.period_lifecycle_service.initialize_after_randomization(
                subject_id=subject.pk,
                actor_user_id=command.actor_id,
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
                    "subject_code": subject.subject_code,
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

    def _apply_subject_identifier_policy(
        self,
        *,
        subject,
        randomization_code: str,
        actor_user_id: int | None,
        now,
    ) -> tuple[str | None, str, str] | None:
        if subject is None:
            raise RandomizeSubjectGateError("Subject was not found for randomization.")
        policy = self.identifier_policy_reader(study_id=subject.study_id)
        if policy is None:
            raise RandomizeSubjectGateError("Study identifier policy was not found.")
        try:
            resolved_subject_code = policy.resolve_from_randomization(
                randomization_code=randomization_code,
                existing_subject_code=subject.subject_code,
            )
        except SubjectIdentifierPolicyError as exc:
            raise RandomizeSubjectGateError(str(exc)) from exc
        if not resolved_subject_code or resolved_subject_code == subject.subject_code:
            return None
        if not self.repository.lock_study_for_identifier_assignment(
            study_id=subject.study_id
        ):
            raise RandomizeSubjectGateError("Study identifier policy was not found.")
        if self.repository.subject_code_exists(
            study_id=subject.study_id,
            site_id=subject.site_id,
            subject_id=subject.pk,
            subject_code=resolved_subject_code,
            uniqueness_scope=policy.normalized_uniqueness_scope.value,
        ):
            raise RandomizeSubjectGateError(
                "Randomization Code is already used as a Subject Code in the configured scope."
            )
        previous_code = self.repository.update_subject_code(
            subject=subject,
            subject_code=resolved_subject_code,
            actor_user_id=actor_user_id,
            now=now,
        )
        return (
            previous_code,
            resolved_subject_code,
            policy.normalized_subject_identifier_mode.value,
        )

    def _record_identifier_change(
        self,
        *,
        subject,
        identifier_change: tuple[str | None, str, str] | None,
        randomization_event_id: int | None,
        actor_user_id: int | None,
        occurred_at,
    ) -> None:
        if identifier_change is None:
            return
        previous_code, subject_code, assignment_source = identifier_change
        self.repository.record_subject_code_assignment(
            subject_id=subject.pk,
            previous_code=previous_code,
            subject_code=subject_code,
            assignment_source=assignment_source,
            related_randomization_event_id=randomization_event_id,
            actor_user_id=actor_user_id,
            occurred_at=occurred_at,
        )


__all__ = [
    "RandomizationSummary",
    "RandomizeSubject",
    "RandomizeSubjectCommand",
    "RandomizeSubjectError",
    "RandomizeSubjectGateError",
    "SubjectRandomized",
]
