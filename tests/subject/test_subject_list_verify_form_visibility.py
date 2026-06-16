from django.test import SimpleTestCase

from apps.subject.application.services.subject_list_verify_form_visibility import (
    SubjectListVerifyFormVisibilityService,
)


class _EditorMapService:
    def __init__(self, editors_by_subject):
        self.editors_by_subject = editors_by_subject

    def map_latest_submitted_entry_updated_by_id_by_subject_ids(self, *, subject_ids):
        return {sid: self.editors_by_subject[sid] for sid in subject_ids if sid in self.editors_by_subject}


class SubjectListVerifyFormVisibilityServiceTests(SimpleTestCase):
    def test_shows_verify_form_for_permitted_user_even_when_user_last_updated_submission(self):
        service = SubjectListVerifyFormVisibilityService(
            editor_map_service=_EditorMapService({1: 7, 2: 8})
        )

        result = service.map_show_verify_form_by_subject_id(
            user_id=7,
            has_verify_form_permission=True,
            subject_ids=(1, 2, 3),
        )

        self.assertEqual(result, {1: True, 2: True, 3: False})

    def test_hides_verify_form_without_permission(self):
        service = SubjectListVerifyFormVisibilityService(
            editor_map_service=_EditorMapService({1: 7})
        )

        result = service.map_show_verify_form_by_subject_id(
            user_id=7,
            has_verify_form_permission=False,
            subject_ids=(1,),
        )

        self.assertEqual(result, {1: False})
