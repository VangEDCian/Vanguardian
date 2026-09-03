import json
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from apps.study.application import StudySubjectIdentifierMigrationBlockedError
from apps.study.presentation.web.views.subject_identifier_policy import (
    StudySubjectIdentifierPolicyPreviewView,
    StudySubjectIdentifierPolicyRollbackView,
)


class StudySubjectIdentifierPolicyMigrationViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_preview_endpoint_returns_counts_and_confirmation_requirement(self):
        preview = _Preview(
            {
                "study_id": 1,
                "plan_hash": "plan-1",
                "enrolled_subjects": 3,
                "requires_confirmation": True,
                "can_execute": True,
            }
        )

        class PreviewService:
            def execute(self, *, study_id, target_values):
                self.__class__.captured = (study_id, target_values)
                return preview

        request = self.factory.post(
            "/studies/1/subject-identifier-policy/preview",
            {
                "code": "NNG31",
                "subject_identifier_mode": "copy_randomization_at_randomization",
                "screening_identifier_mode": "generated",
                "subject_code_pattern": "{study_code}-{sequence:03d}",
                "screening_code_pattern": "{study_code}-S{sequence:03d}",
                "subject_code_uniqueness_scope": "study",
                "lock_subject_code_after_assignment": "on",
            },
        )
        view = StudySubjectIdentifierPolicyPreviewView()
        view._study_id = 1
        view.service_class = PreviewService

        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["enrolled_subjects"], 3)
        self.assertEqual(PreviewService.captured[0], 1)
        self.assertTrue(
            PreviewService.captured[1]["lock_subject_code_after_assignment"]
        )

    def test_rollback_endpoint_returns_conflict_without_writing_audit(self):
        preview = _Preview(
            {
                "plan_hash": "new-plan",
                "can_execute": False,
                "blockers": [{"message": "Subject data changed."}],
            }
        )

        class RollbackService:
            def execute(self, **_kwargs):
                raise StudySubjectIdentifierMigrationBlockedError(preview)

        class AuditService:
            called = False

            def record_updated(self, **_kwargs):
                self.__class__.called = True

        request = self.factory.post(
            "/studies/1/subject-identifier-policy/rollback",
            {"plan_hash": "stale", "confirmation_code": "NNG31"},
        )
        request.user = SimpleNamespace(pk=7)
        view = StudySubjectIdentifierPolicyRollbackView()
        view._study_id = 1
        view.service_class = RollbackService
        view.audit_service_class = AuditService

        response = view.post(request)

        self.assertEqual(response.status_code, 409)
        self.assertFalse(json.loads(response.content)["can_execute"])
        self.assertFalse(AuditService.called)


class _Preview:
    def __init__(self, payload):
        self.payload = payload

    def as_dict(self):
        return self.payload
