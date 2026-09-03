from apps.subject.models import Subject


class DjangoSubjectListActionsRepository:
    @staticmethod
    def get_subject(*, study_id: int, subject_id: int, snapshot_class):
        row = (
            Subject.objects.filter(
                pk=subject_id,
                study_id=study_id,
                deleted=False,
            )
            .values(
                "id",
                "study_id",
                "site_id",
                "subject_code",
                "screening_code",
            )
            .first()
        )
        if row is None:
            return None
        return snapshot_class(
            pk=row["id"],
            study_id=row["study_id"],
            site_id=row["site_id"],
            subject_code=row["subject_code"] or "",
            screening_code=row["screening_code"] or "",
        )


__all__ = ["DjangoSubjectListActionsRepository"]
