from dataclasses import dataclass


@dataclass(frozen=True)
class UpsertSectionTemplateCommand:
    selected_study_id: int
    crf_template_id: int
    section_template_id: int | None
    section_code: str
    vi_name: str
    en_name: str
    vi_description: str
    en_description: str
    vi_help_text: str
    en_help_text: str
    vi_instruction_text: str
    en_instruction_text: str
    display_order: int
    is_required: bool
    is_repeatable: bool
    min_repeats: int
    max_repeats: int | None
    actor_user_id: int


__all__ = ["UpsertSectionTemplateCommand"]
