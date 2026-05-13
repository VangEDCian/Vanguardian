
from apps.datacapture.application.services.subject_submitted_editor_map import (
    DataCaptureSubjectSubmittedEditorMapService,
)

VERIFY_FORM_PERMISSION = "subject.verify_form"


class SubjectListVerifyFormVisibilityService:
    def __init__(self, editor_map_service: DataCaptureSubjectSubmittedEditorMapService | None = None):
        self._editor_map_service = editor_map_service or DataCaptureSubjectSubmittedEditorMapService()

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
        out: dict[int, bool] = {}
        for sid in subject_ids:
            if sid not in editors_by_subject:
                out[sid] = False
                continue
            editor_id = editors_by_subject[sid]
            out[sid] = editor_id is None or user_id != editor_id
        return out
