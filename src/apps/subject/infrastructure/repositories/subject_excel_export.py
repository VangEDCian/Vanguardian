from django.db.models import F

from apps.subject.models import Subject


class DjangoSubjectExcelExportRepository:
    def list_scoped_subject_rows(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
    ) -> tuple[dict, ...]:
        return tuple(
            Subject.objects.filter(
                pk__in=subject_ids,
                study_id=study_id,
                site_id=site_id,
                deleted=False,
            )
            .order_by("current_sequence", "id")
            .annotate(
                randomization_code=F("randomization__randomization_number"),
            )
            .values(
                "id",
                "subject_code",
                "screening_code",
                "randomization_code",
            )
        )


__all__ = ["DjangoSubjectExcelExportRepository"]
