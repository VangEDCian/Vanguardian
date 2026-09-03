from django.test import SimpleTestCase

from apps.study.domain import (
    ScreeningIdentifierMode,
    StudySubjectIdentifierPolicy,
    SubjectIdentifierMode,
    SubjectIdentifierPolicyError,
)


class StudySubjectIdentifierPolicyTests(SimpleTestCase):
    def test_default_policy_keeps_screening_and_subject_codes_separate(self):
        policy = StudySubjectIdentifierPolicy(study_id=1, study_code="ABC")

        screening_codes = policy.generate_for_screening(
            current_sequence=7,
            site_code="SITE-01",
        )
        subject_code = policy.generate_for_enrollment(
            enrollment_sequence=3,
            site_code="SITE-01",
            existing_subject_code=None,
        )

        self.assertIsNone(screening_codes.subject_code)
        self.assertEqual(screening_codes.screening_code, "ABC-S007")
        self.assertEqual(subject_code, "ABC-003")

    def test_copy_mode_assigns_randomization_code_at_randomization_only(self):
        policy = StudySubjectIdentifierPolicy(
            study_id=1,
            study_code="ABC",
            subject_identifier_mode=SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION,
        )

        screening_codes = policy.generate_for_screening(
            current_sequence=1,
            site_code="SITE-01",
        )
        enrollment_code = policy.generate_for_enrollment(
            enrollment_sequence=1,
            site_code="SITE-01",
            existing_subject_code=None,
        )

        self.assertIsNone(screening_codes.subject_code)
        self.assertIsNone(enrollment_code)
        self.assertEqual(
            policy.resolve_from_randomization(
                randomization_code="RND-101",
                existing_subject_code=None,
            ),
            "RND-101",
        )

    def test_external_identifiers_are_required_at_screening(self):
        policy = StudySubjectIdentifierPolicy(
            study_id=1,
            study_code="ABC",
            subject_identifier_mode=SubjectIdentifierMode.EXTERNAL,
            screening_identifier_mode=ScreeningIdentifierMode.EXTERNAL,
        )

        with self.assertRaisesMessage(SubjectIdentifierPolicyError, "Subject Code is required"):
            policy.generate_for_screening(
                current_sequence=1,
                site_code="SITE-01",
                supplied_screening_code="SCR-001",
            )

    def test_locked_subject_code_cannot_be_replaced_by_randomization(self):
        policy = StudySubjectIdentifierPolicy(
            study_id=1,
            study_code="ABC",
            subject_identifier_mode=SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION,
        )

        with self.assertRaisesMessage(SubjectIdentifierPolicyError, "locked"):
            policy.resolve_from_randomization(
                randomization_code="RND-002",
                existing_subject_code="SUB-001",
            )

    def test_pattern_supports_site_code_and_rejects_unknown_placeholders(self):
        policy = StudySubjectIdentifierPolicy(
            study_id=1,
            study_code="ABC",
            subject_identifier_mode=SubjectIdentifierMode.GENERATED_AT_SCREENING,
            subject_code_pattern="{site_code}-{sequence:04d}",
        )

        codes = policy.generate_for_screening(
            current_sequence=12,
            site_code="S01",
        )
        self.assertEqual(codes.subject_code, "S01-0012")

        invalid_policy = StudySubjectIdentifierPolicy(
            study_id=1,
            study_code="ABC",
            subject_code_pattern="{protocol}-{sequence}",
        )
        with self.assertRaisesMessage(SubjectIdentifierPolicyError, "unsupported placeholder"):
            invalid_policy.validate()
