from django.db.models import Q

from apps.crf.models import (
    CrfFieldDefinition,
    CrfFieldDefinitionTranslation,
    CrfFieldReviewPolicy,
    CrfFieldTemplate,
    CrfFieldTemplateTranslation,
    CrfFieldUiConfig,
    CrfFieldUiConfigTranslation,
    CrfFieldValidationRule,
    CrfSectionTemplate,
    CrfTemplate,
)


class DjangoCrfFieldTemplateImportRepository:
    def find_templates_by_name_or_code(self, *, study_id, form_name):
        return (
            CrfTemplate.objects.filter(
                Q(code__iexact=form_name) | Q(translations__name__iexact=form_name),
                study_id=study_id,
                deleted=False,
            )
            .distinct()
            .order_by("pk")
        )

    def find_sections_by_name_or_code(self, *, crf_template_id, section_name):
        return (
            CrfSectionTemplate.objects.filter(
                Q(section_code__iexact=section_name) | Q(translations__section_name__iexact=section_name),
                crf_template_id=crf_template_id,
                deleted=False,
            )
            .distinct()
            .order_by("pk")
        )

    def get_field_template_for_import(self, *, crf_template_id, field_key):
        return CrfFieldTemplate.objects.filter(
            crf_template_id=crf_template_id,
            field_key=field_key,
        ).first()

    def find_field_templates_for_import(self, *, crf_template_id, field_keys):
        normalized_keys = tuple(
            key.strip()
            for key in (field_keys or ())
            if isinstance(key, str) and key.strip()
        )
        if not normalized_keys:
            return []
        return list(
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                field_key__in=normalized_keys,
            ).select_related("definition", "ui_config")
        )

    def build_field_template(self, **values):
        return CrfFieldTemplate(**values)

    def build_field_definition(self, **values):
        return CrfFieldDefinition(**values)

    def build_field_ui_config(self, **values):
        return CrfFieldUiConfig(**values)

    def build_field_template_translation(self, **values):
        return CrfFieldTemplateTranslation(**values)

    def build_field_definition_translation(self, **values):
        return CrfFieldDefinitionTranslation(**values)

    def build_field_ui_config_translation(self, **values):
        return CrfFieldUiConfigTranslation(**values)

    def save_field_template(self, field_template, *, update_fields=None):
        if update_fields is None:
            field_template.save()
        else:
            field_template.save(update_fields=update_fields)
        return field_template

    def update_field_template(self, *, field_template, values):
        CrfFieldTemplate.objects.filter(pk=field_template.pk).update(**values)

    def bulk_create_field_templates(self, *, field_templates):
        if not field_templates:
            return []
        return CrfFieldTemplate.objects.bulk_create(field_templates)

    def bulk_update_field_templates(self, *, field_templates, update_fields):
        if not field_templates:
            return
        CrfFieldTemplate.objects.bulk_update(field_templates, fields=update_fields)

    def bulk_create_field_template_translations(self, *, translations):
        if not translations:
            return []
        return CrfFieldTemplateTranslation.objects.bulk_create(translations)

    def bulk_update_field_template_translations(self, *, translations, update_fields):
        if not translations:
            return
        CrfFieldTemplateTranslation.objects.bulk_update(translations, fields=update_fields)

    def find_field_template_translations(self, *, field_template_ids, language_codes=None):
        normalized_ids = tuple(
            int(field_template_id)
            for field_template_id in (field_template_ids or ())
            if field_template_id is not None
        )
        if not normalized_ids:
            return []
        queryset = CrfFieldTemplateTranslation.objects.filter(master_id__in=normalized_ids)
        if language_codes is not None:
            queryset = queryset.filter(language_code__in=tuple(language_codes))
        return list(queryset)

    def bulk_create_field_definitions(self, *, definitions):
        if not definitions:
            return []
        return CrfFieldDefinition.objects.bulk_create(definitions)

    def bulk_update_field_definitions(self, *, definitions, update_fields):
        if not definitions:
            return
        CrfFieldDefinition.objects.bulk_update(definitions, fields=update_fields)

    def bulk_create_field_definition_translations(self, *, translations):
        if not translations:
            return []
        return CrfFieldDefinitionTranslation.objects.bulk_create(translations)

    def bulk_update_field_definition_translations(self, *, translations, update_fields):
        if not translations:
            return
        CrfFieldDefinitionTranslation.objects.bulk_update(translations, fields=update_fields)

    def find_field_definition_translations(self, *, definition_ids, language_codes=None):
        normalized_ids = tuple(
            int(definition_id)
            for definition_id in (definition_ids or ())
            if definition_id is not None
        )
        if not normalized_ids:
            return []
        queryset = CrfFieldDefinitionTranslation.objects.filter(master_id__in=normalized_ids)
        if language_codes is not None:
            queryset = queryset.filter(language_code__in=tuple(language_codes))
        return list(queryset)

    def bulk_create_field_ui_configs(self, *, ui_configs):
        if not ui_configs:
            return []
        return CrfFieldUiConfig.objects.bulk_create(ui_configs)

    def bulk_update_field_ui_configs(self, *, ui_configs, update_fields):
        if not ui_configs:
            return
        CrfFieldUiConfig.objects.bulk_update(ui_configs, fields=update_fields)

    def bulk_create_field_ui_config_translations(self, *, translations):
        if not translations:
            return []
        return CrfFieldUiConfigTranslation.objects.bulk_create(translations)

    def bulk_update_field_ui_config_translations(self, *, translations, update_fields):
        if not translations:
            return
        CrfFieldUiConfigTranslation.objects.bulk_update(translations, fields=update_fields)

    def find_field_ui_config_translations(self, *, ui_config_ids, language_codes=None):
        normalized_ids = tuple(
            int(ui_config_id)
            for ui_config_id in (ui_config_ids or ())
            if ui_config_id is not None
        )
        if not normalized_ids:
            return []
        queryset = CrfFieldUiConfigTranslation.objects.filter(master_id__in=normalized_ids)
        if language_codes is not None:
            queryset = queryset.filter(language_code__in=tuple(language_codes))
        return list(queryset)

    def save_field_template_translation(self, *, field_template, language_code, label):
        CrfFieldTemplateTranslation.objects.update_or_create(
            master=field_template,
            language_code=language_code,
            defaults={"label": label},
        )

    def create_field_template_translation(self, *, field_template, language_code, label):
        return CrfFieldTemplateTranslation.objects.create(
            master=field_template,
            language_code=language_code,
            label=label,
        )

    def update_field_template_translation(self, *, field_template, language_code, label):
        return CrfFieldTemplateTranslation.objects.filter(
            master=field_template,
            language_code=language_code,
        ).update(label=label)

    def update_field_definition(self, *, field_definition, values):
        if field_definition is None:
            return 0
        return CrfFieldDefinition.objects.filter(pk=field_definition.pk).update(**values)

    def create_field_definition(self, *, field_template, values):
        return CrfFieldDefinition.objects.create(field_template=field_template, **values)

    def save_field_definition_translation(self, *, definition, language_code, values):
        CrfFieldDefinitionTranslation.objects.update_or_create(
            master=definition,
            language_code=language_code,
            defaults=values,
        )

    def create_field_definition_translation(self, *, definition, language_code, values):
        return CrfFieldDefinitionTranslation.objects.create(
            master=definition,
            language_code=language_code,
            **values,
        )

    def update_field_definition_translation(self, *, definition, language_code, values):
        return CrfFieldDefinitionTranslation.objects.filter(
            master=definition,
            language_code=language_code,
        ).update(**values)

    def update_field_ui_config(self, *, ui_config, values):
        if ui_config is None:
            return 0
        return CrfFieldUiConfig.objects.filter(pk=ui_config.pk).update(**values)

    def create_field_ui_config(self, *, field_template, values):
        return CrfFieldUiConfig.objects.create(field_template=field_template, **values)

    def save_field_ui_config_translation(self, *, ui_config, language_code, values):
        CrfFieldUiConfigTranslation.objects.update_or_create(
            master=ui_config,
            language_code=language_code,
            defaults=values,
        )

    def create_field_ui_config_translation(self, *, ui_config, language_code, values):
        return CrfFieldUiConfigTranslation.objects.create(
            master=ui_config,
            language_code=language_code,
            **values,
        )

    def update_field_ui_config_translation(self, *, ui_config, language_code, values):
        return CrfFieldUiConfigTranslation.objects.filter(
            master=ui_config,
            language_code=language_code,
        ).update(**values)

    def get_field_review_policy(
        self,
        *,
        study_id,
        study_version,
        crf_template_id,
        field_template_id,
        review_type,
    ):
        return CrfFieldReviewPolicy.objects.filter(
            study_id=study_id,
            study_version=study_version,
            crf_template_id=crf_template_id,
            field_template_id=field_template_id,
            review_type=review_type,
        ).first()

    def find_field_review_policies_for_import(
        self,
        *,
        study_id,
        crf_template_id,
        field_template_ids,
        study_versions,
        review_types,
    ):
        normalized_field_template_ids = tuple(
            int(field_template_id)
            for field_template_id in (field_template_ids or ())
            if field_template_id is not None
        )
        normalized_study_versions = tuple(
            str(study_version)
            for study_version in (study_versions or ())
            if self._as_text(study_version)
        )
        normalized_review_types = tuple(
            str(review_type)
            for review_type in (review_types or ())
            if self._as_text(review_type)
        )
        if not normalized_field_template_ids:
            return []
        if not normalized_study_versions:
            return []
        if not normalized_review_types:
            return []
        return list(
            CrfFieldReviewPolicy.objects.filter(
                study_id=study_id,
                crf_template_id=crf_template_id,
                field_template_id__in=normalized_field_template_ids,
                study_version__in=normalized_study_versions,
                review_type__in=normalized_review_types,
            )
        )

    @staticmethod
    def _as_text(raw_value):
        return str(raw_value or "").strip()

    def create_field_review_policy(self, **values):
        return CrfFieldReviewPolicy.objects.create(**values)

    def save_field_review_policy(self, field_review_policy, *, update_fields):
        field_review_policy.save(update_fields=update_fields)
        return field_review_policy

    def reset_template_fields_for_import(self, *, crf_template_id, actor_user_id, now):
        field_ids = tuple(
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                deleted=False,
            ).values_list("id", flat=True)
        )
        if not field_ids:
            return 0

        CrfFieldTemplate.objects.filter(id__in=field_ids).update(
            deleted=True,
            is_active=False,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        CrfFieldDefinition.objects.filter(
            field_template_id__in=field_ids,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        CrfFieldUiConfig.objects.filter(
            field_template_id__in=field_ids,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        CrfFieldValidationRule.objects.filter(
            field_template_id__in=field_ids,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        CrfFieldReviewPolicy.objects.filter(
            field_template_id__in=field_ids,
            deleted=False,
        ).update(
            deleted=True,
            is_enabled=False,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        return len(field_ids)
