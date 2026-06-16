from dataclasses import dataclass


@dataclass(frozen=True)
class UpsertCrfTemplateCommand:
    selected_study_id: int
    study_id: int
    code: str
    version: str
    vi_name: str
    en_name: str
    actor_user_id: int


__all__ = ["UpsertCrfTemplateCommand"]
