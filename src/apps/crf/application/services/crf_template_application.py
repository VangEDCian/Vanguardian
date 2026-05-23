from apps.crf.application.commands import (
    UpsertCrfTemplateCommand,
    UpsertSectionLayoutConfigCommand,
    UpsertSectionTemplateCommand,
)
from apps.crf.application.services.crf_template_command import CrfTemplateCommandService
from apps.crf.application.services.crf_template_query import CrfTemplateQueryService


class CrfTemplateApplicationService:
    query_service_class = CrfTemplateQueryService
    command_service_class = CrfTemplateCommandService

    def __init__(self, *, query_service=None, command_service=None):
        self.query_service = query_service or self.query_service_class()
        self.command_service = command_service or self.command_service_class()

    def get_crf_template_model(self):
        return self.query_service.get_crf_template_model()

    def list_study_templates_for_listing(self, *, study_id):
        return self.query_service.list_study_templates_for_listing(
            study_id=study_id,
        )

    def list_study_crf_navigation(self, *, study_id):
        return self.query_service.list_study_crf_navigation(study_id=study_id)

    def list_study_templates_by_code(self, *, study_id, code):
        return self.query_service.list_study_templates_by_code(
            study_id=study_id,
            code=code,
        )

    def resolve_unique_template_by_code_version(self, *, study_id, code, version):
        return self.query_service.resolve_unique_template_by_code_version(
            study_id=study_id,
            code=code,
            version=version,
        )

    def resolve_unique_template_by_code(
        self,
        *,
        study_id,
        code,
        case_insensitive=False,
    ):
        return self.query_service.resolve_unique_template_by_code(
            study_id=study_id,
            code=code,
            case_insensitive=case_insensitive,
        )

    def upsert_crf_template(
        self,
        *,
        selected_study_id,
        study_id,
        code,
        version,
        vi_name,
        en_name,
        actor_user_id,
        now=None,
    ):
        return self.command_service.upsert_crf_template(
            UpsertCrfTemplateCommand(
                selected_study_id=selected_study_id,
                study_id=study_id,
                code=code,
                version=version,
                vi_name=vi_name,
                en_name=en_name,
                actor_user_id=actor_user_id,
            ),
            now=now,
        )

    def upsert_section_template(
        self,
        *,
        selected_study_id,
        crf_template_id,
        section_template_id,
        section_code,
        vi_name,
        en_name,
        vi_description,
        en_description,
        vi_help_text,
        en_help_text,
        vi_instruction_text,
        en_instruction_text,
        display_order,
        is_required,
        is_repeatable,
        min_repeats,
        max_repeats,
        actor_user_id,
        now=None,
    ):
        return self.command_service.upsert_section_template(
            UpsertSectionTemplateCommand(
                selected_study_id=selected_study_id,
                crf_template_id=crf_template_id,
                section_template_id=section_template_id,
                section_code=section_code,
                vi_name=vi_name,
                en_name=en_name,
                vi_description=vi_description,
                en_description=en_description,
                vi_help_text=vi_help_text,
                en_help_text=en_help_text,
                vi_instruction_text=vi_instruction_text,
                en_instruction_text=en_instruction_text,
                display_order=display_order,
                is_required=is_required,
                is_repeatable=is_repeatable,
                min_repeats=min_repeats,
                max_repeats=max_repeats,
                actor_user_id=actor_user_id,
            ),
            now=now,
        )

    def list_template_fields_with_ui_config(self, *, template_id):
        return self.query_service.list_template_fields_with_ui_config(
            template_id=template_id,
        )

    def upsert_section_layout_config(
        self,
        *,
        selected_study_id,
        section_template_id,
        layout_type,
        column_count,
        label_position,
        density,
        section_style,
        is_collapsible,
        is_expanded_by_default,
        show_section_header,
        show_border,
        show_background,
        custom_css_class,
        custom_layout_schema,
        actor_user_id,
        now=None,
    ):
        return self.command_service.upsert_section_layout_config(
            UpsertSectionLayoutConfigCommand(
                selected_study_id=selected_study_id,
                section_template_id=section_template_id,
                layout_type=layout_type,
                column_count=column_count,
                label_position=label_position,
                density=density,
                section_style=section_style,
                is_collapsible=is_collapsible,
                is_expanded_by_default=is_expanded_by_default,
                show_section_header=show_section_header,
                show_border=show_border,
                show_background=show_background,
                custom_css_class=custom_css_class,
                custom_layout_schema=custom_layout_schema,
                actor_user_id=actor_user_id,
            ),
            now=now,
        )


__all__ = ["CrfTemplateApplicationService"]
