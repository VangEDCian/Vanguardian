
VERIFY_FORM_PERMISSION = "subject.verify_form"


class SubjectListVerifyFormVisibilityService:
    def __init__(self, editor_map_service=None):
        if editor_map_service is None:
            from apps.datacapture.application.services.subject_submitted_editor_map import (
                DataCaptureSubjectSubmittedEditorMapService,
            )

            editor_map_service = DataCaptureSubjectSubmittedEditorMapService()
        self._editor_map_service = editor_map_service

    def map_show_verify_form_by_subject_id(
        self,
        *,
        user_id: int,
        has_verify_form_permission: bool,
        subject_ids: tuple[int, ...],
    ) -> dict[int, bool]:
        if not has_verify_form_permission:
            return {sid: False for sid in subject_ids}

        editors_by_subject = self._editor_map_service.map_latest_submitted_entry_updated_by_id_by_subject_ids(
            subject_ids=subject_ids
        )
        _ = user_id
        return {sid: sid in editors_by_subject for sid in subject_ids}
