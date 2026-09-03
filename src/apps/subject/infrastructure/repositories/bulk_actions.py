from dataclasses import dataclass

from django.utils import timezone

from apps.subject.infrastructure.persistence.models import Subject


@dataclass(frozen=True)
class SubjectBulkActionSnapshot:
    subject_id: int
    subject_code: str | None
    screening_code: str | None
    lifecycle_status: str

    def as_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "subject_code": self.subject_code,
            "screening_code": self.screening_code,
            "lifecycle_status": self.lifecycle_status,
            "deleted": False,
        }


class DjangoSubjectBulkActionRepository:
    def list_scoped_subject_ids(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
    ) -> tuple[int, ...]:
        return tuple(
            Subject.objects.filter(
                pk__in=subject_ids,
                study_id=study_id,
                site_id=site_id,
                deleted=False,
            )
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    def list_scoped_subjects_for_update(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
    ) -> tuple[SubjectBulkActionSnapshot, ...]:
        subjects = (
            Subject.objects.select_for_update()
            .filter(
                pk__in=subject_ids,
                study_id=study_id,
                site_id=site_id,
                deleted=False,
            )
            .order_by("pk")
        )
        return tuple(
            SubjectBulkActionSnapshot(
                subject_id=subject.pk,
                subject_code=subject.subject_code,
                screening_code=subject.screening_code,
                lifecycle_status=subject.lifecycle_status,
            )
            for subject in subjects
        )

    def soft_delete_subjects(
        self,
        *,
        subject_ids: tuple[int, ...],
        actor_user_id: int | None,
    ) -> int:
        if not subject_ids:
            return 0
        return Subject.objects.filter(
            pk__in=subject_ids,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=timezone.now(),
            updated_by_id=actor_user_id,
        )


__all__ = [
    "DjangoSubjectBulkActionRepository",
    "SubjectBulkActionSnapshot",
]
