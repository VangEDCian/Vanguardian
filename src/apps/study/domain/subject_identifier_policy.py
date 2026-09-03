from dataclasses import dataclass
from enum import StrEnum
from string import Formatter

MAX_IDENTIFIER_LENGTH = 64
DEFAULT_SUBJECT_CODE_PATTERN = "{study_code}-{sequence:03d}"
DEFAULT_SCREENING_CODE_PATTERN = "{study_code}-S{sequence:03d}"


class SubjectIdentifierPolicyError(ValueError):
    """Raised when a study identifier policy cannot produce a safe identifier."""


class SubjectIdentifierMode(StrEnum):
    GENERATED_AT_SCREENING = "generated_at_screening"
    GENERATED_AT_ENROLLMENT = "generated_at_enrollment"
    COPY_RANDOMIZATION_AT_RANDOMIZATION = "copy_randomization_at_randomization"
    EXTERNAL = "external"


class ScreeningIdentifierMode(StrEnum):
    GENERATED = "generated"
    EXTERNAL = "external"
    DISABLED = "disabled"


class SubjectCodeUniquenessScope(StrEnum):
    STUDY_SITE = "study_site"
    STUDY = "study"


@dataclass(frozen=True)
class StudySubjectGeneratedCodes:
    subject_code: str | None = None
    screening_code: str | None = None


@dataclass(frozen=True)
class StudySubjectIdentifierPolicy:
    study_id: int
    study_code: str
    subject_identifier_mode: str = SubjectIdentifierMode.GENERATED_AT_ENROLLMENT
    screening_identifier_mode: str = ScreeningIdentifierMode.GENERATED
    subject_code_pattern: str = DEFAULT_SUBJECT_CODE_PATTERN
    screening_code_pattern: str = DEFAULT_SCREENING_CODE_PATTERN
    subject_code_uniqueness_scope: str = SubjectCodeUniquenessScope.STUDY_SITE
    lock_subject_code_after_assignment: bool = True

    @property
    def normalized_subject_identifier_mode(self) -> SubjectIdentifierMode:
        try:
            return SubjectIdentifierMode(self.subject_identifier_mode)
        except ValueError as exc:
            raise SubjectIdentifierPolicyError(
                f"Unsupported subject identifier mode: {self.subject_identifier_mode}."
            ) from exc

    @property
    def normalized_screening_identifier_mode(self) -> ScreeningIdentifierMode:
        try:
            return ScreeningIdentifierMode(self.screening_identifier_mode)
        except ValueError as exc:
            raise SubjectIdentifierPolicyError(
                f"Unsupported screening identifier mode: {self.screening_identifier_mode}."
            ) from exc

    @property
    def normalized_uniqueness_scope(self) -> SubjectCodeUniquenessScope:
        try:
            return SubjectCodeUniquenessScope(self.subject_code_uniqueness_scope)
        except ValueError as exc:
            raise SubjectIdentifierPolicyError(
                f"Unsupported subject code uniqueness scope: {self.subject_code_uniqueness_scope}."
            ) from exc

    @property
    def requires_subject_code_on_create(self) -> bool:
        return self.normalized_subject_identifier_mode is SubjectIdentifierMode.EXTERNAL

    @property
    def requires_screening_code_on_create(self) -> bool:
        return self.normalized_screening_identifier_mode is ScreeningIdentifierMode.EXTERNAL

    def validate(self) -> None:
        subject_mode = self.normalized_subject_identifier_mode
        screening_mode = self.normalized_screening_identifier_mode
        self.normalized_uniqueness_scope
        if subject_mode in (
            SubjectIdentifierMode.GENERATED_AT_SCREENING,
            SubjectIdentifierMode.GENERATED_AT_ENROLLMENT,
        ):
            self._validate_pattern(self.subject_code_pattern, label="Subject Code")
        if screening_mode is ScreeningIdentifierMode.GENERATED:
            self._validate_pattern(self.screening_code_pattern, label="Screening Code")

    def generate_for_screening(
        self,
        *,
        current_sequence: int,
        site_code: str,
        supplied_subject_code: str | None = None,
        supplied_screening_code: str | None = None,
    ) -> StudySubjectGeneratedCodes:
        self.validate()
        subject_mode = self.normalized_subject_identifier_mode
        screening_mode = self.normalized_screening_identifier_mode

        subject_code = None
        if subject_mode is SubjectIdentifierMode.GENERATED_AT_SCREENING:
            subject_code = self._render_pattern(
                self.subject_code_pattern,
                current_sequence=current_sequence,
                site_code=site_code,
                label="Subject Code",
            )
        elif subject_mode is SubjectIdentifierMode.EXTERNAL:
            subject_code = self._require_supplied_identifier(
                supplied_subject_code,
                label="Subject Code",
            )
        elif supplied_subject_code:
            raise SubjectIdentifierPolicyError(
                "Subject Code cannot be supplied for the configured identifier mode."
            )

        screening_code = None
        if screening_mode is ScreeningIdentifierMode.GENERATED:
            screening_code = self._render_pattern(
                self.screening_code_pattern,
                current_sequence=current_sequence,
                site_code=site_code,
                label="Screening Code",
            )
        elif screening_mode is ScreeningIdentifierMode.EXTERNAL:
            screening_code = self._require_supplied_identifier(
                supplied_screening_code,
                label="Screening Code",
            )
        elif supplied_screening_code:
            raise SubjectIdentifierPolicyError(
                "Screening Code cannot be supplied when screening identifiers are disabled."
            )

        return StudySubjectGeneratedCodes(
            subject_code=subject_code,
            screening_code=screening_code,
        )

    def generate_for_enrollment(
        self,
        *,
        enrollment_sequence: int,
        site_code: str,
        existing_subject_code: str | None,
    ) -> str | None:
        self.validate()
        existing = self._normalize_optional_identifier(existing_subject_code)
        mode = self.normalized_subject_identifier_mode
        if existing:
            return existing
        if mode is SubjectIdentifierMode.GENERATED_AT_ENROLLMENT:
            return self._render_pattern(
                self.subject_code_pattern,
                current_sequence=enrollment_sequence,
                site_code=site_code,
                label="Subject Code",
            )
        if mode in (
            SubjectIdentifierMode.GENERATED_AT_SCREENING,
            SubjectIdentifierMode.EXTERNAL,
        ):
            raise SubjectIdentifierPolicyError(
                "Subject Code must be assigned before enrollment for the configured identifier mode."
            )
        return None

    def generate_subject_code_for_sequence(
        self,
        *,
        sequence: int,
        site_code: str,
    ) -> str:
        """Render a Subject Code without applying lifecycle preservation rules.

        Policy migrations use this operation to compute the desired value for
        an existing subject. Runtime screening/enrollment assignment continues
        to use the lifecycle-specific methods above.
        """
        self.validate()
        if self.normalized_subject_identifier_mode not in (
            SubjectIdentifierMode.GENERATED_AT_SCREENING,
            SubjectIdentifierMode.GENERATED_AT_ENROLLMENT,
        ):
            raise SubjectIdentifierPolicyError(
                "The configured identifier mode does not generate Subject Codes."
            )
        return self._render_pattern(
            self.subject_code_pattern,
            current_sequence=sequence,
            site_code=site_code,
            label="Subject Code",
        )

    def resolve_from_randomization(
        self,
        *,
        randomization_code: str | None,
        existing_subject_code: str | None,
    ) -> str | None:
        self.validate()
        if (
            self.normalized_subject_identifier_mode
            is not SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
        ):
            return self._normalize_optional_identifier(existing_subject_code)

        resolved_code = self._require_supplied_identifier(
            randomization_code,
            label="Randomization Code",
        )
        existing = self._normalize_optional_identifier(existing_subject_code)
        if existing and existing != resolved_code and self.lock_subject_code_after_assignment:
            raise SubjectIdentifierPolicyError(
                "Subject Code is locked and does not match the assigned Randomization Code."
            )
        return resolved_code

    def _render_pattern(
        self,
        pattern: str,
        *,
        current_sequence: int,
        site_code: str,
        label: str,
    ) -> str:
        self._validate_pattern(pattern, label=label)
        try:
            rendered = pattern.format(
                study_code=self.study_code.strip(),
                site_code=str(site_code or "").strip(),
                sequence=current_sequence,
            )
        except (KeyError, ValueError) as exc:
            raise SubjectIdentifierPolicyError(
                f"{label} pattern could not be rendered."
            ) from exc
        return self._validate_identifier(rendered, label=label)

    @staticmethod
    def _validate_pattern(pattern: str, *, label: str) -> None:
        normalized = str(pattern or "").strip()
        if not normalized:
            raise SubjectIdentifierPolicyError(f"{label} pattern is required.")
        fields = []
        try:
            parsed = list(Formatter().parse(normalized))
        except ValueError as exc:
            raise SubjectIdentifierPolicyError(f"{label} pattern is invalid.") from exc
        for _literal, field_name, _format_spec, conversion in parsed:
            if field_name is None:
                continue
            if field_name not in {"study_code", "site_code", "sequence"}:
                raise SubjectIdentifierPolicyError(
                    f"{label} pattern contains unsupported placeholder: {field_name}."
                )
            if conversion:
                raise SubjectIdentifierPolicyError(
                    f"{label} pattern conversions are not supported."
                )
            fields.append(field_name)
        if "sequence" not in fields:
            raise SubjectIdentifierPolicyError(
                f"{label} pattern must contain the sequence placeholder."
            )

    @classmethod
    def _require_supplied_identifier(cls, value: str | None, *, label: str) -> str:
        normalized = cls._normalize_optional_identifier(value)
        if not normalized:
            raise SubjectIdentifierPolicyError(f"{label} is required by the study policy.")
        return cls._validate_identifier(normalized, label=label)

    @staticmethod
    def _normalize_optional_identifier(value: str | None) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @staticmethod
    def _validate_identifier(value: str, *, label: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise SubjectIdentifierPolicyError(f"{label} cannot be empty.")
        if len(normalized) > MAX_IDENTIFIER_LENGTH:
            raise SubjectIdentifierPolicyError(
                f"{label} cannot exceed {MAX_IDENTIFIER_LENGTH} characters."
            )
        return normalized


__all__ = [
    "DEFAULT_SCREENING_CODE_PATTERN",
    "DEFAULT_SUBJECT_CODE_PATTERN",
    "MAX_IDENTIFIER_LENGTH",
    "ScreeningIdentifierMode",
    "StudySubjectGeneratedCodes",
    "StudySubjectIdentifierPolicy",
    "SubjectCodeUniquenessScope",
    "SubjectIdentifierMode",
    "SubjectIdentifierPolicyError",
]
