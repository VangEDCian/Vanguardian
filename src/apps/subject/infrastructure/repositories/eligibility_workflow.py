from django.db import transaction
from django.utils import timezone

from apps.subject.models import (
    Subject,
    SubjectEnrollment,
    SubjectEventInstance,
    SubjectRandomization,
    SubjectStatusHistory,
)


class DjangoSubjectEligibilityWorkflowRepository:
    def get_subject_scope(self, *, study_id: int, site_id: int, subject_id: int):
        return (
            Subject.objects.filter(
                pk=subject_id,
                study_id=study_id,
                site_id=site_id,
                deleted=False,
            )
            .only("id", "study_id", "site_id")
            .first()
        )

    def get_event_scope(self, *, event_instance_id: int):
        return (
            SubjectEventInstance.objects.filter(pk=event_instance_id, deleted=False)
            .only("id", "event_definition_id", "study_version")
            .first()
        )

    def is_subject_randomized(self, *, study_id: int, subject_id: int) -> bool:
        return SubjectRandomization.objects.filter(
            study_id=study_id,
            subject_id=subject_id,
            deleted=False,
            randomization_number__isnull=False,
        ).exists()

    def is_subject_enrolled(self, *, study_id: int, subject_id: int) -> bool:
        return SubjectEnrollment.objects.filter(
            study_id=study_id,
            subject_id=subject_id,
            deleted=False,
            is_enrolled=True,
        ).exists()

    def transition_enrollment_status(
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
        screen_failure_status: str,
        screened_status: str,
    ):
        now = timezone.now()
        with transaction.atomic():
            subject = (
                Subject.objects.select_for_update()
                .filter(pk=subject_id, study_id=study_id, site_id=site_id, deleted=False)
                .first()
            )
            if subject is None:
                return None

            enrollment, _ = SubjectEnrollment.objects.select_for_update().get_or_create(
                subject_id=subject_id,
                defaults={
                    "created_at": now,
                    "updated_at": now,
                    "deleted": False,
                    "status": screened_status,
                    "status_datetime": now,
                    "site_id": site_id,
                    "study_id": study_id,
                    "created_by_id": actor_user_id,
                    "updated_by_id": actor_user_id,
                },
            )
            from_status = enrollment.status
            enrollment.status = to_status
            enrollment.status_datetime = now
            enrollment.status_reason_code = reason_code
            enrollment.status_reason_text = reason_text
            enrollment.is_enrolled = is_enrolled
            enrollment.updated_at = now
            enrollment.updated_by_id = actor_user_id
            if is_enrolled:
                enrollment.enrollment_date = now.date()
                enrollment.enrolled_by_id = actor_user_id
            if to_status == screen_failure_status:
                enrollment.screen_failed_at = now
            enrollment.save()

            SubjectStatusHistory.objects.create(
                subject_id=subject_id,
                from_status=from_status,
                to_status=to_status,
                transition_at=now,
                reason_code=reason_code,
                reason_text=reason_text,
                source=source,
                changed_by_id=actor_user_id,
            )
        return {
            "subject_id": subject_id,
            "from_status": from_status,
            "to_status": to_status,
            "is_enrolled": is_enrolled,
            "status_datetime": now,
        }


__all__ = ["DjangoSubjectEligibilityWorkflowRepository"]
