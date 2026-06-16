from apps.crf.models import (
    CrfFieldDefinition,
    CrfFieldTemplate,
    CrfFieldUiConfig,
    CrfSectionLayoutConfig,
    CrfSectionTemplate,
    CrfTemplate,
)


class DjangoCrfTemplateRepository:
    def get_crf_template_model(self):
        return CrfTemplate

    def list_study_templates_for_listing(self, *, study_id):
        return CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
        ).prefetch_related("translations")

    def list_study_crf_navigation_templates(self, *, study_id):
        return (
            CrfTemplate.objects.filter(
                study_id=study_id,
                deleted=False,
            )
            .prefetch_related("translations")
            .order_by("code", "id")
        )

    def list_study_templates_by_code(self, *, study_id, code):
        return CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
            code=code,
        ).order_by("version", "id")

    def find_unique_template_by_code_version(self, *, study_id, code, version):
        return CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
            code=code,
            version=version,
        ).order_by("pk")

    def find_unique_template_by_code(self, *, study_id, code, case_insensitive=False):
        lookup_key = "code__iexact" if case_insensitive else "code"
        return CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
            **{lookup_key: code},
        ).order_by("pk")

    def list_template_fields_with_related_config(self, *, template_id):
        return (
            CrfFieldTemplate.objects.filter(
                crf_template_id=template_id,
                section_template_id__isnull=False,
                deleted=False,
                is_active=True,
            )
            .select_related("section_template", "section_template__layout_config")
            .prefetch_related("translations", "section_template__translations")
            .order_by(
                "section_template__display_order",
                "section_template__id",
                "display_order",
                "id",
            )
        )

    def list_field_definitions_by_field_template_ids(self, field_template_ids):
        return (
            CrfFieldDefinition.objects.filter(
                field_template_id__in=field_template_ids,
                deleted=False,
            )
            .prefetch_related("translations")
        )

    def list_field_ui_configs_by_field_template_ids(self, field_template_ids):
        return (
            CrfFieldUiConfig.objects.filter(
                field_template_id__in=field_template_ids,
                deleted=False,
            )
            .prefetch_related("translations")
        )

    def get_template_for_upsert(self, *, study_id, code, version):
        return CrfTemplate.objects.filter(
            study_id=study_id,
            code=code,
            version=version,
        ).first()

    def build_template(self, **values):
        return CrfTemplate(**values)

    def save_template(self, crf_template):
        crf_template.save()
        return crf_template

    def get_template(self, *, template_id):
        return CrfTemplate.objects.filter(
            pk=template_id,
            deleted=False,
        ).first()

    def get_section_template(self, *, section_template_id, crf_template_id):
        return CrfSectionTemplate.objects.filter(
            pk=section_template_id,
            crf_template_id=crf_template_id,
        ).first()

    def get_section_template_by_id(self, *, section_template_id):
        return (
            CrfSectionTemplate.objects.filter(
                pk=section_template_id,
                deleted=False,
            )
            .select_related("crf_template")
            .first()
        )

    def build_section_template(self, **values):
        return CrfSectionTemplate(**values)

    def save_section_template(self, section_template):
        section_template.save()
        return section_template

    def get_section_layout_config(self, *, section_template_id):
        return CrfSectionLayoutConfig.objects.filter(
            section_template_id=section_template_id,
        ).first()

    def build_section_layout_config(self, **values):
        return CrfSectionLayoutConfig(**values)

    def save_section_layout_config(self, layout_config):
        layout_config.save()
        return layout_config
