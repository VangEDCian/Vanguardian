from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.study.models import Study
from apps.subject.models import (
    Subject,
    SubjectEnrollment,
    SubjectEventInstance,
    SubjectIdentifierHistory,
    SubjectRandomization,
    SubjectStatusHistory,
)


class DjangoSubjectEligibilityWorkflowRepository:
    @staticmethod
    def lock_study_for_identifier_assignment(*, study_id: int) -> bool:
        return Study.objects.select_for_update().filter(
            pk=study_id,
            deleted=False,
        ).exists()

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

    @staticmethod
    def get_subject_for_identifier_assignment(
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
    ):
        return (
            Subject.objects.select_for_update()
            .select_related("site")
            .filter(
                pk=subject_id,
                study_id=study_id,
                site_id=site_id,
                deleted=False,
            )
            .first()
        )

    @staticmethod
    def get_next_enrollment_sequence(*, study_id: int) -> int:
        current_max = Subject.objects.filter(
            study_id=study_id,
            enrollment_current_sequence__isnull=False,
        ).aggregate(max_sequence=Max("enrollment_current_sequence"))["max_sequence"]
        return int(current_max or 0) + 1

    @staticmethod
    def subject_code_exists(
        *,
        study_id: int,
        site_id: int,
        subject_id: int,
        subject_code: str,
        uniqueness_scope: str,
    ) -> bool:
        queryset = Subject.objects.filter(
            study_id=study_id,
            subject_code=subject_code,
            deleted=False,
        ).exclude(pk=subject_id)
        if uniqueness_scope == "study_site":
            queryset = queryset.filter(site_id=site_id)
        return queryset.exists()

    @staticmethod
    def assign_subject_identifier(
        *,
        subject,
        enrollment_sequence: int,
        subject_code: str | None,
        assignment_source: str,
        actor_user_id: int | None,
        now,
    ) -> None:
        previous_subject_code = str(subject.subject_code or "").strip() or None
        subject.enrollment_current_sequence = enrollment_sequence
        subject.subject_code = subject_code
        subject.updated_at = now
        subject.updated_by_id = actor_user_id
        subject.save(
            update_fields=[
                "enrollment_current_sequence",
                "subject_code",
                "updated_at",
                "updated_by_id",
            ]
        )
        if subject_code and subject_code != previous_subject_code:
            SubjectIdentifierHistory.objects.create(
                subject_id=subject.pk,
                identifier_type="subject_code",
                from_value=previous_subject_code,
                to_value=subject_code,
                assignment_source=assignment_source,
                occurred_at=now,
                actor_user_id=actor_user_id,
            )


__all__ = ["DjangoSubjectEligibilityWorkflowRepository"]
