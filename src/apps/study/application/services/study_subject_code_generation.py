from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class StudySubjectGeneratedCodes:
    subject_code: str | None = None
    screening_code: str | None = None


class StudySubjectScreeningCodeIncrementalService:
    FLAG = "screening_code_incremental"

    @classmethod
    def is_enabled(cls, mode: str) -> bool:
        return mode == cls.FLAG

    @staticmethod
    def generate(*, study_code: str, current_sequence: int) -> StudySubjectGeneratedCodes:
        sequence = str(current_sequence).rjust(3, "0")
        return StudySubjectGeneratedCodes(
            subject_code=None,
            screening_code=f"{study_code}-S{sequence}",
        )


class StudySubjectCodeIncrementalService:
    FLAG = "subject_code_incremental"

    @classmethod
    def is_enabled(cls, mode: str) -> bool:
        return mode == cls.FLAG

    @staticmethod
    def generate(*, study_code: str, current_sequence: int) -> StudySubjectGeneratedCodes:
        sequence = str(current_sequence).rjust(3, "0")
        return StudySubjectGeneratedCodes(
            subject_code=f"{study_code}-{sequence}",
            screening_code=None,
        )


class StudySubjectCodeGenerationService:
    def __init__(self, mode: str | None = None):
        self.mode = (mode or settings.STUDY_SUBJECT_CODE_GENERATION_MODE or "").strip().lower()

    def generate(self, *, study_code: str, current_sequence: int) -> StudySubjectGeneratedCodes:
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
