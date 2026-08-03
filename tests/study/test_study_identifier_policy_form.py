from pathlib import Path

from django.test import SimpleTestCase

from apps.study.presentation.web.forms import StudyForm


class StudyIdentifierPolicyFormTests(SimpleTestCase):
    def test_accepts_explicit_per_study_identifier_policy(self):
        form = StudyForm(
            {
                "code": "ABC",
                "name": "ABC Study",
                "sponsor": "Sponsor",
                "description": "",
                "is_active": "on",
                "subject_identifier_mode": "copy_randomization_at_randomization",
                "screening_identifier_mode": "external",
                "subject_code_pattern": "{study_code}-{sequence:03d}",
                "screening_code_pattern": "{site_code}-S{sequence:04d}",
                "subject_code_uniqueness_scope": "study",
                "lock_subject_code_after_assignment": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["subject_identifier_mode"],
            "copy_randomization_at_randomization",
        )
        self.assertEqual(form.cleaned_data["screening_identifier_mode"], "external")
        self.assertEqual(form.cleaned_data["subject_code_uniqueness_scope"], "study")

    def test_rejects_unsupported_identifier_pattern_placeholder(self):
        form = StudyForm(
            {
                "code": "ABC",
                "name": "ABC Study",
                "subject_identifier_mode": "generated_at_enrollment",
                "screening_identifier_mode": "generated",
                "subject_code_pattern": "{protocol}-{sequence}",
                "screening_code_pattern": "{study_code}-S{sequence:03d}",
                "subject_code_uniqueness_scope": "study_site",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("unsupported placeholder", str(form.non_field_errors()))

    def test_study_create_and_detail_templates_include_policy_fields(self):
        for template_path in (
            "src/templates/study/study_form.html",
            "src/templates/study/study_detail.html",
        ):
            source = Path(template_path).read_text()
            self.assertIn("_subject_identifier_policy_fields.html", source)
