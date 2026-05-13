from apps.datacapture.application import (
    DataCapturePageStateEventTransitionService,
    DataCapturePageStateNotFoundError,
    DataCaptureSaveSubmitPageService,
    DeleteDraftPageCommand,
    SavePageCommand,
    SubmitPageCommand,
    TriggerPageStateEventTransitionCommand,
)
from apps.datacapture.application.services.page_entry_read import DataCapturePageEntryReadService
from apps.datacapture.application.services.page_state_read import DataCapturePageStateReadService
from apps.datacapture.application.services.page_state_write import DataCapturePageStateWriteService


def trigger_event_transition_for_page_state(
    *,
    page_state_id: int,
    actor_user_id: int | None = None,
    trigger_source: str = "datacapture",
):
    command = TriggerPageStateEventTransitionCommand(
        page_state_id=page_state_id,
        actor_user_id=actor_user_id,
        trigger_source=trigger_source,
    )
    return DataCapturePageStateEventTransitionService().execute(command)


def save_page_for_subject_visit_crf(
    *, subject_id: int, visit_id: int, crf_template_id: int, data: str, actor_user_id: int | None = None
):
    return DataCaptureSaveSubmitPageService().save(
        SavePageCommand(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            data=data,
            actor_user_id=actor_user_id,
        )
    )


def submit_page_for_subject_visit_crf(
    *, subject_id: int, visit_id: int, crf_template_id: int, data: str, actor_user_id: int | None = None
):
    return DataCaptureSaveSubmitPageService().submit(
        SubmitPageCommand(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            data=data,
            actor_user_id=actor_user_id,
        )
    )


def delete_latest_draft_page_entry_for_subject_visit_crf(
    *, subject_id: int, visit_id: int, crf_template_id: int, actor_user_id: int | None = None
):
    return DataCaptureSaveSubmitPageService().delete_latest_draft(
        DeleteDraftPageCommand(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            actor_user_id=actor_user_id,
        )
    )


def get_page_state_status_for_subject_visit_crf(
    *, subject_id: int, visit_id: int | None, crf_template_id: int
) -> str:
    """Return ``PageState.status`` for the scope, or empty string if none."""
    if visit_id is None:
        return ""
    return DataCapturePageStateReadService().get_page_state_status(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def get_page_state_id_for_subject_visit_crf(
    *, subject_id: int, visit_id: int | None, crf_template_id: int
) -> int | None:
    if visit_id is None:
        return None
    return DataCapturePageStateReadService().get_page_state_id_for_scope(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def get_page_state_final_data_for_subject_visit_crf(
    *, subject_id: int, visit_id: int | None, crf_template_id: int
) -> dict:
    if visit_id is None:
        return {}
    return DataCapturePageStateReadService().get_page_state_final_data_map(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def get_latest_page_entry_for_subject_visit_crf(
    *, subject_id: int, visit_id: int | None, crf_template_id: int
):
    if visit_id is None:
        return None
    return DataCapturePageEntryReadService().get_latest_page_entry(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def get_latest_submitted_page_entry_for_subject_visit_crf(
    *, subject_id: int, visit_id: int | None, crf_template_id: int
):
    if visit_id is None:
        return None
    return DataCapturePageEntryReadService().get_latest_submitted_page_entry(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def merge_form_verification_checked_fields_into_page_state_final_data(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    checked_field_template_ids: list[int],
    actor_user_id: int | None = None,
) -> tuple[bool, str]:
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().merge_checked_field_template_ids(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        checked_field_template_ids=checked_field_template_ids,
        actor_user_id=actor_user_id,
    )


def ensure_draft_page_state_if_not_exists(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    actor_user_id: int | None = None,
) -> bool:
    """Create draft ``PageState`` when missing. ``final_data`` stays NULL until form verification."""
    return DataCapturePageStateWriteService().ensure_draft_if_not_exists(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        actor_user_id=actor_user_id,
    )


__all__ = [
    "DataCapturePageStateNotFoundError",
    "delete_latest_draft_page_entry_for_subject_visit_crf",
    "ensure_draft_page_state_if_not_exists",
    "get_latest_page_entry_for_subject_visit_crf",
    "get_latest_submitted_page_entry_for_subject_visit_crf",
    "get_page_state_final_data_for_subject_visit_crf",
    "get_page_state_id_for_subject_visit_crf",
    "get_page_state_status_for_subject_visit_crf",
    "merge_form_verification_checked_fields_into_page_state_final_data",
    "save_page_for_subject_visit_crf",
    "submit_page_for_subject_visit_crf",
    "trigger_event_transition_for_page_state",
]
