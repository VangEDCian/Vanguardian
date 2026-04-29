from apps.crf.application import (
    CrfTemplateAmbiguousError,
    CrfTemplateApplicationService,
    CrfTemplateNotFoundError,
)
from apps.crf.models import CrfSectionTemplate


class CrfContextAdapter:
    def __init__(self, crf_template_service=None):
        self.crf_template_service = crf_template_service or CrfTemplateApplicationService()

    def get_crf_template_model(self):
        return self.crf_template_service.get_crf_template_model()

    def list_study_templates_for_listing(self, *, study_id):
        return self.crf_template_service.list_study_templates_for_listing(study_id=study_id)

    def list_study_templates_by_code(self, *, study_id, code):
        return self.crf_template_service.list_study_templates_by_code(
            study_id=study_id,
            code=code,
        )

    def list_study_crf_navigation(self, *, study_id):
        return self.crf_template_service.list_study_crf_navigation(study_id=study_id)

    def list_template_fields_with_ui_config(self, *, template_id):
        return self.crf_template_service.list_template_fields_with_ui_config(
            template_id=template_id,
        )

    def resolve_unique_template_by_code(self, *, study_id, code, case_insensitive=False):
        return self.crf_template_service.resolve_unique_template_by_code(
            study_id=study_id,
            code=code,
            case_insensitive=case_insensitive,
        )

    def resolve_unique_template_by_code_version(self, *, study_id, code, version):
        return self.crf_template_service.resolve_unique_template_by_code_version(
            study_id=study_id,
            code=code,
            version=version,
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
        return self.crf_template_service.upsert_crf_template(
            selected_study_id=selected_study_id,
            study_id=study_id,
            code=code,
            version=version,
            vi_name=vi_name,
            en_name=en_name,
            actor_user_id=actor_user_id,
            now=now,
        )

    def upsert_section_template(
        self,
        *,
        selected_study_id,
        crf_template_id,
        section_template_id=None,
        section_code,
        vi_name,
        en_name,
        vi_description=None,
        en_description=None,
        vi_help_text=None,
        en_help_text=None,
        vi_instruction_text=None,
        en_instruction_text=None,
        display_order,
        is_required,
        is_repeatable,
        min_repeats,
        max_repeats,
        actor_user_id,
        now=None,
    ):
        is_legacy_import_contract = (
            section_template_id is None
            and vi_description is None
            and en_description is None
            and vi_help_text is None
            and en_help_text is None
            and vi_instruction_text is None
            and en_instruction_text is None
        )

        import_outcome = None
        resolved_section_template_id = section_template_id
        if resolved_section_template_id is None:
            existing_section_template = CrfSectionTemplate.objects.filter(
                crf_template_id=crf_template_id,
                section_code=section_code,
            ).first()
            if existing_section_template is not None:
                resolved_section_template_id = existing_section_template.pk
                import_outcome = "updated"
            else:
                import_outcome = "created"

        result = self.crf_template_service.upsert_section_template(
            selected_study_id=selected_study_id,
            crf_template_id=crf_template_id,
            section_template_id=resolved_section_template_id,
            section_code=section_code,
            vi_name=vi_name,
            en_name=en_name,
            vi_description=vi_description or "",
            en_description=en_description or "",
            vi_help_text=vi_help_text or "",
            en_help_text=en_help_text or "",
            vi_instruction_text=vi_instruction_text or "",
            en_instruction_text=en_instruction_text or "",
            display_order=display_order,
            is_required=is_required,
            is_repeatable=is_repeatable,
            min_repeats=min_repeats,
            max_repeats=max_repeats,
            actor_user_id=actor_user_id,
            now=now,
        )
        if is_legacy_import_contract:
            return import_outcome or "updated"
        return result


def get_crf_template_model():
    return CrfContextAdapter().get_crf_template_model()


__all__ = [
    "CrfContextAdapter",
    "CrfTemplateNotFoundError",
    "CrfTemplateAmbiguousError",
    "get_crf_template_model",
]
