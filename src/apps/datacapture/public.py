from apps.datacapture.application import (
    DataCapturePageStateEventTransitionService,
    DataCapturePageStateNotFoundError,
    DataCaptureSaveSubmitPageService,
    DeleteDraftPageCommand,
    SavePageCommand,
    SubmitPageCommand,
    TriggerPageStateEventTransitionCommand,
)
from apps.datacapture.application.services.fact_snapshot import DataCaptureFactSnapshotService
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


def read_fact_snapshot_for_page_state(*, page_state_id: int):
    return DataCaptureFactSnapshotService().read_for_page_state(page_state_id=page_state_id)


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
    unverify_reason_text: str | None = None,
    actor_user_id: int | None = None,
) -> tuple[bool, str, list[str], list[int]]:
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().merge_checked_field_template_ids(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        checked_field_template_ids=checked_field_template_ids,
        unverify_reason_text=unverify_reason_text,
        actor_user_id=actor_user_id,
    )


def get_verified_or_waived_field_template_ids_for_subject_visit_crf(
    *,
    subject_id: int,
    visit_id: int | None,
    crf_template_id: int,
) -> set[int]:
    if visit_id is None:
        return set()
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().list_verified_or_waived_field_template_ids(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def get_verified_field_template_ids_for_subject_visit_crf(
    *,
    subject_id: int,
    visit_id: int | None,
    crf_template_id: int,
) -> set[int]:
    if visit_id is None:
        return set()
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().list_verified_field_template_ids(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )


def is_field_verified_for_page_state(
    *,
    page_state_id: int,
    field_template_id: int,
) -> bool:
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().is_field_verified_for_page_state(
        page_state_id=page_state_id,
        field_template_id=field_template_id,
    )


def reopen_verified_form_verification_page_state(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    reason_text: str | None,
    actor_user_id: int | None = None,
) -> str:
    from apps.datacapture.application.services.page_state_verification_final_data import (
        DataCapturePageStateVerificationFinalDataService,
    )

    return DataCapturePageStateVerificationFinalDataService().reopen_verified_page_state(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        reason_text=reason_text,
        actor_user_id=actor_user_id,
    )


def ensure_draft_page_state_if_not_exists(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    actor_user_id: int | None = None,
) -> bool:
    """Create not-started ``PageState`` when missing. ``final_data`` uses empty JSON until finalized."""
    return DataCapturePageStateWriteService().ensure_open_if_not_exists(
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
    "get_verified_field_template_ids_for_subject_visit_crf",
    "get_verified_or_waived_field_template_ids_for_subject_visit_crf",
    "is_field_verified_for_page_state",
    "merge_form_verification_checked_fields_into_page_state_final_data",
    "read_fact_snapshot_for_page_state",
    "reopen_verified_form_verification_page_state",
    "save_page_for_subject_visit_crf",
    "submit_page_for_subject_visit_crf",
    "trigger_event_transition_for_page_state",
]
