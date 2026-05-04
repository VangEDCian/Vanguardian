from apps.datacapture.application import (
    DataCapturePageStateEventTransitionService,
    DataCapturePageStateNotFoundError,
    DataCaptureSaveSubmitPageService,
    SavePageCommand,
    SubmitPageCommand,
    TriggerPageStateEventTransitionCommand,
)
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


def ensure_draft_page_state_if_not_exists(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    final_data: str = "{}",
    actor_user_id: int | None = None,
) -> bool:
    """Create draft ``PageState`` when missing. Other apps must use this instead of ORM on ``DataCapturePageState``."""
    return DataCapturePageStateWriteService().ensure_draft_if_not_exists(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        final_data=final_data,
        actor_user_id=actor_user_id,
    )


__all__ = [
    "DataCapturePageStateNotFoundError",
    "ensure_draft_page_state_if_not_exists",
    "get_page_state_status_for_subject_visit_crf",
    "save_page_for_subject_visit_crf",
    "submit_page_for_subject_visit_crf",
    "trigger_event_transition_for_page_state",
]
