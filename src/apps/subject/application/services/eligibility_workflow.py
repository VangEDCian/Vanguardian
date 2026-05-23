from dataclasses import dataclass

from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError
from apps.subject.infrastructure.repositories.eligibility_workflow import (
    DjangoSubjectEligibilityWorkflowRepository,
)


class SubjectEligibilityWorkflowError(ApplicationValidationError):
    default_message = "Subject eligibility workflow operation failed."


class SubjectEligibilityWorkflowNotFoundError(ApplicationNotFoundError):
    default_message = "Subject was not found for eligibility workflow."


@dataclass(frozen=True)
class SubjectScopeSnapshot:
    subject_id: int
    study_id: int
    site_id: int


@dataclass(frozen=True)
class SubjectEventScopeSnapshot:
    event_instance_id: int
    event_definition_id: int
    study_version: str


@dataclass(frozen=True)
class SubjectEnrollmentTransitionResult:
    subject_id: int
    from_status: str | None
    to_status: str
    is_enrolled: bool
    status_datetime: object


class SubjectEligibilityWorkflowService:
    repository_class = DjangoSubjectEligibilityWorkflowRepository

    ELIGIBLE_STATUS = "Eligible"
    ENROLLED_STATUS = "Enrolled"
    SCREEN_FAILURE_STATUS = "ScreenFailure"
    SCREENED_STATUS = "Screened"

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_subject_scope(self, *, study_id: int, site_id: int, subject_id: int) -> SubjectScopeSnapshot:
        subject = self.repository.get_subject_scope(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
        )
        if subject is None:
            raise SubjectEligibilityWorkflowNotFoundError()
        return SubjectScopeSnapshot(
            subject_id=subject.pk,
            study_id=subject.study_id,
            site_id=subject.site_id,
        )

    def get_event_scope(self, *, event_instance_id: int) -> SubjectEventScopeSnapshot | None:
        event_instance = self.repository.get_event_scope(event_instance_id=event_instance_id)
        if event_instance is None:
            return None
        return SubjectEventScopeSnapshot(
            event_instance_id=event_instance.pk,
            event_definition_id=event_instance.event_definition_id,
            study_version=event_instance.study_version,
        )

    def mark_eligible_from_assessment(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        actor_user_id: int | None,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> SubjectEnrollmentTransitionResult:
        return self._transition_enrollment_status(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
            to_status=self.ELIGIBLE_STATUS,
            is_enrolled=False,
            actor_user_id=actor_user_id,
            source="eligibility",
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def mark_screen_failure_from_assessment(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        actor_user_id: int | None,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> SubjectEnrollmentTransitionResult:
        return self._transition_enrollment_status(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
            to_status=self.SCREEN_FAILURE_STATUS,
            is_enrolled=False,
            actor_user_id=actor_user_id,
            source="eligibility",
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def mark_screened_after_retract(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        actor_user_id: int | None,
        reason_code: str | None,
        reason_text: str | None,
    ) -> SubjectEnrollmentTransitionResult:
        return self._transition_enrollment_status(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
            to_status=self.SCREENED_STATUS,
            is_enrolled=False,
            actor_user_id=actor_user_id,
            source="eligibility",
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def enroll_subject(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        actor_user_id: int | None,
        reason_code: str | None = None,
        reason_text: str | None = None,
    ) -> SubjectEnrollmentTransitionResult:
        return self._transition_enrollment_status(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
            to_status=self.ENROLLED_STATUS,
            is_enrolled=True,
            actor_user_id=actor_user_id,
            source="eligibility",
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def is_subject_randomized(self, *, study_id: int, subject_id: int) -> bool:
        return self.repository.is_subject_randomized(
            study_id=study_id,
            subject_id=subject_id,
        )

    def is_subject_enrolled(self, *, study_id: int, subject_id: int) -> bool:
        return self.repository.is_subject_enrolled(
            study_id=study_id,
            subject_id=subject_id,
        )

    def _transition_enrollment_status(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        to_status: str,
        is_enrolled: bool,
        actor_user_id: int | None,
        source: str,
        reason_code: str | None,
        reason_text: str | None,
    ) -> SubjectEnrollmentTransitionResult:
        result = self.repository.transition_enrollment_status(
            study_id=study_id,
            site_id=site_id,
            subject_id=subject_id,
            to_status=to_status,
            is_enrolled=is_enrolled,
            actor_user_id=actor_user_id,
            source=source,
            reason_code=reason_code,
            reason_text=reason_text,
            screen_failure_status=self.SCREEN_FAILURE_STATUS,
            screened_status=self.SCREENED_STATUS,
        )
        if result is None:
            raise SubjectEligibilityWorkflowNotFoundError()

        return SubjectEnrollmentTransitionResult(
            subject_id=subject_id,
            from_status=result["from_status"],
            to_status=to_status,
            is_enrolled=is_enrolled,
            status_datetime=result["status_datetime"],
        )


__all__ = [
    "SubjectEligibilityWorkflowError",
    "SubjectEligibilityWorkflowNotFoundError",
    "SubjectEligibilityWorkflowService",
    "SubjectEnrollmentTransitionResult",
    "SubjectEventScopeSnapshot",
    "SubjectScopeSnapshot",
]
