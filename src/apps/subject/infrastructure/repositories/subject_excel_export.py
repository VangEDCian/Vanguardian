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
            .values(
                "id",
                "subject_code",
                "screening_code",
            )
        )


__all__ = ["DjangoSubjectExcelExportRepository"]
