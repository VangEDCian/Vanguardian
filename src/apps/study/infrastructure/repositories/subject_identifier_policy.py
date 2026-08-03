from apps.study.models import Study


class DjangoStudySubjectIdentifierPolicyRepository:
    def get_policy_values(self, *, study_id: int) -> dict | None:
        return (
            Study.objects.filter(pk=study_id, deleted=False)
            .values(
                "id",
                "code",
                "subject_identifier_mode",
                "screening_identifier_mode",
                "subject_code_pattern",
                "screening_code_pattern",
                "subject_code_uniqueness_scope",
                "lock_subject_code_after_assignment",
            )
            .first()
        )


__all__ = ["DjangoStudySubjectIdentifierPolicyRepository"]
