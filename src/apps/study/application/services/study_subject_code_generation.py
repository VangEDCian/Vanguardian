from django.conf import settings

from apps.study.domain import (
    DEFAULT_SCREENING_CODE_PATTERN,
    DEFAULT_SUBJECT_CODE_PATTERN,
    ScreeningIdentifierMode,
    StudySubjectGeneratedCodes,
    StudySubjectIdentifierPolicy,
    SubjectCodeUniquenessScope,
    SubjectIdentifierMode,
)
from apps.study.infrastructure.repositories import (
    DjangoStudySubjectIdentifierPolicyRepository,
)


class StudySubjectScreeningCodeIncrementalService:
    """Compatibility formatter for the legacy screening-code strategy."""

    FLAG = "screening_code_incremental"

    @classmethod
    def is_enabled(cls, mode: str) -> bool:
        return mode == cls.FLAG

    @staticmethod
    def generate(*, study_code: str, current_sequence: int) -> StudySubjectGeneratedCodes:
        return StudySubjectGeneratedCodes(
            screening_code=DEFAULT_SCREENING_CODE_PATTERN.format(
                study_code=study_code,
                sequence=current_sequence,
            )
        )


class StudySubjectCodeIncrementalService:
    """Compatibility formatter for the legacy subject-code strategy."""

    FLAG = "subject_code_incremental"

    @classmethod
    def is_enabled(cls, mode: str) -> bool:
        return mode == cls.FLAG

    @staticmethod
    def generate(*, study_code: str, current_sequence: int) -> StudySubjectGeneratedCodes:
        return StudySubjectGeneratedCodes(
            subject_code=DEFAULT_SUBJECT_CODE_PATTERN.format(
                study_code=study_code,
                sequence=current_sequence,
            )
        )


class StudySubjectCodeGenerationService:
    """Policy renderer with a compatibility path for legacy callers."""

    def __init__(self, mode: str | None = None):
        self.mode = str(
            mode
            or settings.STUDY_SUBJECT_CODE_GENERATION_MODE
            or StudySubjectScreeningCodeIncrementalService.FLAG
        ).strip().lower()

    def generate(
        self,
        *,
        study_code: str,
        current_sequence: int,
    ) -> StudySubjectGeneratedCodes:
        if StudySubjectScreeningCodeIncrementalService.is_enabled(self.mode):
            return StudySubjectScreeningCodeIncrementalService.generate(
                study_code=study_code,
                current_sequence=current_sequence,
            )
        if StudySubjectCodeIncrementalService.is_enabled(self.mode):
            return StudySubjectCodeIncrementalService.generate(
                study_code=study_code,
                current_sequence=current_sequence,
            )
        return StudySubjectGeneratedCodes()

    def generate_for_screening(
        self,
        *,
        policy: StudySubjectIdentifierPolicy,
        current_sequence: int,
        site_code: str,
        supplied_subject_code: str | None = None,
        supplied_screening_code: str | None = None,
    ) -> StudySubjectGeneratedCodes:
        return policy.generate_for_screening(
            current_sequence=current_sequence,
            site_code=site_code,
            supplied_subject_code=supplied_subject_code,
            supplied_screening_code=supplied_screening_code,
        )


class StudySubjectIdentifierPolicyQueryService:
    repository_class = DjangoStudySubjectIdentifierPolicyRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_policy(self, *, study_id: int) -> StudySubjectIdentifierPolicy | None:
        values = self.repository.get_policy_values(study_id=study_id)
        if values is None:
            return None
        return StudySubjectIdentifierPolicy(
            study_id=int(values["id"]),
            study_code=str(values["code"]),
            subject_identifier_mode=values["subject_identifier_mode"],
            screening_identifier_mode=values["screening_identifier_mode"],
            subject_code_pattern=values["subject_code_pattern"],
            screening_code_pattern=values["screening_code_pattern"],
            subject_code_uniqueness_scope=values["subject_code_uniqueness_scope"],
            lock_subject_code_after_assignment=bool(
                values["lock_subject_code_after_assignment"]
            ),
        )


def default_subject_identifier_policy(*, study_id: int, study_code: str):
    return StudySubjectIdentifierPolicy(
        study_id=study_id,
        study_code=study_code,
        subject_identifier_mode=SubjectIdentifierMode.GENERATED_AT_ENROLLMENT,
        screening_identifier_mode=ScreeningIdentifierMode.GENERATED,
        subject_code_uniqueness_scope=SubjectCodeUniquenessScope.STUDY_SITE,
    )


__all__ = [
    "StudySubjectCodeGenerationService",
    "StudySubjectCodeIncrementalService",
    "StudySubjectGeneratedCodes",
    "StudySubjectIdentifierPolicyQueryService",
    "StudySubjectScreeningCodeIncrementalService",
    "default_subject_identifier_policy",
]
