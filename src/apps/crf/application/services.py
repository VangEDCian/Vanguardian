from django.db import transaction
from django.utils import timezone

from apps.crf.models import (
    CrfFieldDefinition,
    CrfFieldTemplate,
    CrfFieldUiConfig,
    CrfSectionTemplate,
    CrfTemplate,
)


class CrfTemplateNotFoundError(Exception):
    """Raised when a CRF template cannot be found for the requested selector."""


class CrfTemplateAmbiguousError(Exception):
    """Raised when a CRF template selector matches more than one template."""


class CrfTemplateApplicationService:
    template_model = CrfTemplate
    section_template_model = CrfSectionTemplate
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
        crf_templates = list(
            self.template_model.objects.filter(
                study_id=study_id,
                deleted=False,
            ).prefetch_related("translations").order_by("code", "id")
        )

        payload = []
        for crf_template in crf_templates:
            template_name = crf_template.safe_translation_getter(
                "name",
                default=crf_template.code,
                any_language=True,
            )
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

    def resolve_unique_template_by_code(
        self,
        *,
        study_id,
        code,
        case_insensitive=False,
    ):
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

    def upsert_crf_template(
        self,
        *,
        study_id,
        code,
        version,
        vi_name,
        en_name,
        actor_user_id,
        now=None,
    ):
        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "is_active": True,
            "updated_at": timestamp,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            crf_template = self.template_model.objects.filter(
                study_id=study_id,
                code=code,
                version=version,
            ).first()

            if crf_template is None:
                crf_template = self.template_model(
                    study_id=study_id,
                    code=code,
                    version=version,
                    created_at=timestamp,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                import_outcome = "created"
            else:
                for field_name, value in defaults.items():
                    setattr(crf_template, field_name, value)
                import_outcome = "updated"

            self._set_translated_value(crf_template, "name", "vi", vi_name)
            self._set_translated_value(crf_template, "name", "en", en_name)
            crf_template.save()
            return import_outcome

    def upsert_section_template(
        self,
        *,
        crf_template_id,
        section_code,
        vi_name,
        en_name,
        display_order,
        is_required,
        is_repeatable,
        min_repeats,
        max_repeats,
        actor_user_id,
        now=None,
    ):
        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "display_order": display_order,
            "is_required": is_required,
            "is_enabled": True,
            "is_repeatable": is_repeatable,
            "min_repeats": min_repeats,
            "max_repeats": max_repeats,
            "updated_at": timestamp,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            section_template = self.section_template_model.objects.filter(
                crf_template_id=crf_template_id,
                section_code=section_code,
            ).first()

            if section_template is None:
                section_template = self.section_template_model(
                    crf_template_id=crf_template_id,
                    section_code=section_code,
                    created_at=timestamp,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                import_outcome = "created"
            else:
                for field_name, value in defaults.items():
                    setattr(section_template, field_name, value)
                import_outcome = "updated"

            self._set_translated_value(section_template, "section_name", "vi", vi_name)
            self._set_translated_value(section_template, "section_name", "en", en_name)
            section_template.save()
            return import_outcome

    def list_template_fields_with_ui_config(self, *, template_id):
        field_templates = list(
            self.field_template_model.objects.filter(
                crf_template_id=template_id,
                crf_template_id__isnull=False,
                section_template_id__isnull=False,
                deleted=False,
                is_active=True,
            )
            .select_related("section_template")
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
            field_label = field_template.safe_translation_getter(
                "label",
                default=field_template.field_key,
                any_language=True,
            )
            section_template = field_template.section_template
            section_payload = None
            if section_template is not None:
                section_payload = {
                    "id": str(section_template.pk),
                    "code": section_template.section_code,
                    "name": section_template.safe_translation_getter(
                        "section_name",
                        default=section_template.section_code,
                        any_language=True,
                    ),
                    "display_order": section_template.display_order,
                    "is_required": section_template.is_required,
                    "is_repeatable": section_template.is_repeatable,
                    "min_repeats": section_template.min_repeats,
                    "max_repeats": section_template.max_repeats,
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
                        "layout": ui_config.layout if ui_config else None,
                        "text": ui_config.text if ui_config else None,
                        "behavior": ui_config.behavior if ui_config else None,
                        "options": ui_config.options if ui_config else None,
                        "style": ui_config.style if ui_config else None,
                    },
                }
            )

        return payload

    @staticmethod
    def _set_translated_value(instance, field_name, language_code, value):
        instance.set_current_language(language_code, initialize=True)
        setattr(instance, field_name, value)
