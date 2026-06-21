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
            .prefetch_related("translations")
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
            .prefetch_related("translations")
            .distinct()
            .order_by("pk")
        )

    def get_field_template_for_import(self, *, crf_template_id, field_key):
        return CrfFieldTemplate.objects.filter(
            crf_template_id=crf_template_id,
            field_key=field_key,
        ).first()

    def build_field_template(self, **values):
        return CrfFieldTemplate(**values)

    def save_field_template(self, field_template):
        field_template.save()
        return field_template

    def save_field_template_translation(self, *, field_template, language_code, label):
        CrfFieldTemplateTranslation.objects.update_or_create(
            master=field_template,
            language_code=language_code,
            defaults={"label": label},
        )

    def save_field_definition(self, *, field_template, values):
        definition, _ = CrfFieldDefinition.objects.update_or_create(
            field_template=field_template,
            defaults=values,
        )
        return definition

    def save_field_definition_translation(self, *, definition, language_code, values):
        CrfFieldDefinitionTranslation.objects.update_or_create(
            master=definition,
            language_code=language_code,
            defaults=values,
        )

    def save_field_ui_config(self, *, field_template, values):
        ui_config, _ = CrfFieldUiConfig.objects.update_or_create(
            field_template=field_template,
            defaults=values,
        )
        return ui_config

    def save_field_ui_config_translation(self, *, ui_config, language_code, values):
        CrfFieldUiConfigTranslation.objects.update_or_create(
            master=ui_config,
            language_code=language_code,
            defaults=values,
        )

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
