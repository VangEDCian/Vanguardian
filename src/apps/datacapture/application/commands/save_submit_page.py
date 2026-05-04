from dataclasses import dataclass


@dataclass(frozen=True)
class SavePageCommand:
    subject_id: int
    visit_id: int
    crf_template_id: int
    data: str
    actor_user_id: int | None = None


@dataclass(frozen=True)
class SubmitPageCommand:
    subject_id: int
    visit_id: int
    crf_template_id: int
    data: str
    actor_user_id: int | None = None


__all__ = [
    "SavePageCommand",
    "SubmitPageCommand",
]
