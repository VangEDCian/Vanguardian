from apps.crf.application.exceptions import (
    CrfTemplateAmbiguousError,
    CrfTemplateNotFoundError,
)
from django.utils.translation import get_language

from apps.crf.models import (
    CrfFieldDefinition,
    CrfFieldTemplate,
    CrfFieldUiConfig,
    CrfTemplate,
)


class CrfTemplateQueryService:
    template_model = CrfTemplate
    field_template_model = CrfFieldTemplate
    field_definition_model = CrfFieldDefinition
    field_ui_config_model = CrfFieldUiConfig

    def get_crf_template_model(self):
        return self.template_model

    def list_study_templates_for_listing(self, *, study_id):
        return self.template_model.objects.filter(
            study_id=study_id,
            deleted=False,
        ).prefetch_related("translations")

    def list_study_crf_navigation(self, *, study_id):
        current_language = self._normalize_language_code(get_language())
        crf_templates = list(
            self.template_model.objects.filter(
                study_id=study_id,
                deleted=False,
            ).prefetch_related("translations").order_by("code", "id")
        )

        payload = []
        for crf_template in crf_templates:
            template_name = self._translated_value(crf_template, current_language, "name", default=crf_template.code)
            payload.append(
                {
                    "id": str(crf_template.pk),
                    "code": crf_template.code,
                    "name": template_name,
                    "version": crf_template.version,
                    "pages": [
                        {
                            "id": f"crf-{crf_template.pk}-main",
                            "code": crf_template.code,
                            "title": template_name,
                            "order": 1,
                        }
                    ],
                }
            )

        return payload

    def list_study_templates_by_code(self, *, study_id, code):
        return list(
            self.template_model.objects.filter(
                study_id=study_id,
                deleted=False,
                code=code,
            ).order_by("version", "id")
        )

    def resolve_unique_template_by_code_version(self, *, study_id, code, version):
        queryset = self.template_model.objects.filter(
            study_id=study_id,
            deleted=False,
            code=code,
            version=version,
        ).order_by("pk")

        count = queryset.count()
        if count == 0:
            raise CrfTemplateNotFoundError(
                f"CRF template with code '{code}' and version '{version}' was not found for study '{study_id}'."
            )
        if count > 1:
            raise CrfTemplateAmbiguousError(
                f"CRF template code '{code}' and version '{version}' is ambiguous for study '{study_id}'."
            )
        return queryset.first()

    def resolve_unique_template_by_code(self, *, study_id, code, case_insensitive=False):
        lookup_key = "code__iexact" if case_insensitive else "code"
        queryset = self.template_model.objects.filter(
            study_id=study_id,
            deleted=False,
            **{lookup_key: code},
        ).order_by("pk")

        count = queryset.count()
        if count == 0:
            raise CrfTemplateNotFoundError(
                f"CRF template with code '{code}' was not found for study '{study_id}'."
            )
        if count > 1:
            raise CrfTemplateAmbiguousError(
                f"CRF template code '{code}' is ambiguous for study '{study_id}'."
            )
        return queryset.first()

    def list_template_fields_with_ui_config(self, *, template_id):
        current_language = self._normalize_language_code(get_language())
        field_templates = list(
            self.field_template_model.objects.filter(
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
        if not field_templates:
            return []

        field_template_ids = [field_template.pk for field_template in field_templates]
        field_definition_map = {
            field_definition.field_template_id: field_definition
            for field_definition in self.field_definition_model.objects.filter(
                field_template_id__in=field_template_ids,
                deleted=False,
            )
        }
        ui_config_map = {
            ui_config.field_template_id: ui_config
            for ui_config in self.field_ui_config_model.objects.filter(
                field_template_id__in=field_template_ids,
                deleted=False,
            )
        }

        payload = []
        for field_template in field_templates:
            field_definition = field_definition_map.get(field_template.pk)
            ui_config = ui_config_map.get(field_template.pk)
            field_label = self._translated_value(
                field_template,
                current_language,
                "label",
                default=field_template.field_key,
            )

            section_template = field_template.section_template
            section_payload = None
            if section_template is not None:
                layout_config = getattr(section_template, "layout_config", None)
                layout_payload = None
                if layout_config is not None and not layout_config.deleted:
                    layout_payload = {
                        "layout_type": layout_config.layout_type,
                        "column_count": layout_config.column_count,
                        "label_position": layout_config.label_position,
                        "density": layout_config.density,
                        "section_style": layout_config.section_style,
                        "is_collapsible": layout_config.is_collapsible,
                        "is_expanded_by_default": layout_config.is_expanded_by_default,
                        "show_section_header": layout_config.show_section_header,
                        "show_border": layout_config.show_border,
                        "show_background": layout_config.show_background,
                        "custom_css_class": layout_config.custom_css_class,
                        "custom_layout_schema": layout_config.custom_layout_schema,
                    }
                section_payload = {
                    "id": str(section_template.pk),
                    "code": section_template.section_code,
                    "name": self._translated_value(
                        section_template,
                        current_language,
                        "section_name",
                        default=section_template.section_code,
                    ),
                    "display_order": section_template.display_order,
                    "is_required": section_template.is_required,
                    "is_repeatable": section_template.is_repeatable,
                    "min_repeats": section_template.min_repeats,
                    "max_repeats": section_template.max_repeats,
                    "layout_config": layout_payload,
                }

            payload.append(
                {
                    "id": str(field_template.pk),
                    "field_key": field_template.field_key,
                    "label": field_label,
                    "data_type": field_template.data_type,
                    "display_order": field_template.display_order,
                    "section_template": section_payload,
                    "data_semantic": field_definition.data_semantic if field_definition else None,
                    "comments": field_definition.comments if field_definition else None,
                    "unit": field_definition.unit if field_definition else None,
                    "codelist": field_definition.codelist if field_definition else None,
                    "text_max_length": field_definition.text_max_length if field_definition else None,
                    "text_min_length": field_definition.text_min_length if field_definition else None,
                    "pattern": field_definition.pattern if field_definition else None,
                    "ui_config": {
                        "control_type": ui_config.control_type if ui_config else None,
                        "control_layout": ui_config.control_layout if ui_config else None,
                        "layout": ui_config.layout if ui_config else None,
                        "text": ui_config.text if ui_config else None,
                        "behavior": ui_config.behavior if ui_config else None,
                        "options": ui_config.options if ui_config else None,
                        "style": ui_config.style if ui_config else None,
                        "classes": ui_config.classes if ui_config else None,
                    },
                }
            )

        return payload

    @staticmethod
    def _translated_value(instance, language_code, field_name, default=""):
        if hasattr(instance, "safe_translation_getter"):
            value = instance.safe_translation_getter(
                field_name,
                default=default,
                language_code=language_code,
                any_language=False,
            )
            if value not in (None, ""):
                return value
            fallback = instance.safe_translation_getter(
                field_name,
                default=default,
                any_language=True,
            )
            return fallback or default
        return getattr(instance, field_name, default) or default

    @staticmethod
    def _normalize_language_code(language_code):
        normalized = (language_code or "en").strip().lower()
        return normalized.split("-", 1)[0]
