from dataclasses import dataclass


@dataclass(frozen=True)
class SavePageCommand:
    subject_id: int
    visit_id: int
    crf_template_id: int
    data: str
    event_form_binding_id: int | None = None
    actor_user_id: int | None = None


@dataclass(frozen=True)
class SubmitFieldChangeReason:
    field_key: str
    field_label: str
    reason: str


@dataclass(frozen=True)
class SubmitPageCommand:
    subject_id: int
    visit_id: int
    crf_template_id: int
    data: str
    event_form_binding_id: int | None = None
    change_reasons: tuple[SubmitFieldChangeReason, ...] = ()
    actor_user_id: int | None = None


@dataclass(frozen=True)
class DeleteDraftPageCommand:
    subject_id: int
    visit_id: int
    crf_template_id: int
    event_form_binding_id: int | None = None
    actor_user_id: int | None = None


__all__ = [
    "DeleteDraftPageCommand",
    "SavePageCommand",
    "SubmitFieldChangeReason",
    "SubmitPageCommand",
]
