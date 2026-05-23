from dataclasses import dataclass


@dataclass(frozen=True)
class UpsertSectionLayoutConfigCommand:
    selected_study_id: int
    section_template_id: int
    layout_type: str
    column_count: int
    label_position: str
    density: str
    section_style: str
    is_collapsible: bool
    is_expanded_by_default: bool
    show_section_header: bool
    show_border: bool
    show_background: bool
    custom_css_class: str | None
    custom_layout_schema: dict | None
    actor_user_id: int


__all__ = ["UpsertSectionLayoutConfigCommand"]
