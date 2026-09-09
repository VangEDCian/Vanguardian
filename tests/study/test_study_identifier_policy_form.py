from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import RequestFactory, SimpleTestCase

from apps.study.application import CreateStudyCommand
from apps.study.presentation.web.forms import StudyForm
from apps.study.presentation.web.views.study_actions import StudyCreateView


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


class StudyCreateViewTests(SimpleTestCase):
    def test_post_ignores_update_only_identifier_migration_fields(self):
        request = RequestFactory().post(
            "/studies/new",
            {
                "code": "ABC",
                "name": "ABC Study",
                "sponsor": "Sponsor",
                "description": "",
                "is_active": "on",
                "subject_identifier_mode": "generated_at_enrollment",
                "screening_identifier_mode": "generated",
                "subject_code_pattern": "{study_code}-{sequence:03d}",
                "screening_code_pattern": "{study_code}-S{sequence:03d}",
                "subject_code_uniqueness_scope": "study_site",
                "lock_subject_code_after_assignment": "on",
                "subject_identifier_migration_plan_hash": "update-only-plan",
                "subject_identifier_migration_confirmation_code": "ABC",
            },
        )
        request.user = SimpleNamespace(pk=7, is_authenticated=True)
        study = SimpleNamespace(pk=11)
        create_service = MagicMock()
        create_service.execute.return_value = study
        audit_service = MagicMock()
        view = StudyCreateView()
        view.create_study_service_class = MagicMock(return_value=create_service)
        view.study_audit_service_class = MagicMock(return_value=audit_service)

        response = view.post(request)

        self.assertEqual(response.status_code, 302)
        command = create_service.execute.call_args.args[0]
        self.assertIsInstance(command, CreateStudyCommand)
        self.assertEqual(command.code, "ABC")
        audit_service.record_created.assert_called_once()
