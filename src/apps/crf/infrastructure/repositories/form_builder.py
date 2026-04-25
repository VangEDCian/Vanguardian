import json
from django.utils import timezone
from django.db.models import Prefetch

from apps.crf.domain.repositories import (
    FormBuilderCommandRepository,
    FormBuilderQueryRepository,
)
from apps.crf.models import (
    CrfFieldDefinition,
    CrfFieldTemplate,
    CrfFieldUiConfig,
    CrfFieldValidationRule,
    CrfSectionTemplate,
    CrfSectionLayoutConfig,
    CrfTemplate,
)


class DjangoOrmFormBuilderRepository(FormBuilderCommandRepository, FormBuilderQueryRepository):
    def get_form_by_scope(self, *, study_id, form_id):
        return CrfTemplate.objects.filter(
            pk=form_id,
            study_id=study_id,
            deleted=False,
        ).first()

    def get_field_by_scope(self, *, study_id, form_id, field_id):
        return CrfFieldTemplate.objects.filter(
            pk=field_id,
            crf_template_id=form_id,
            crf_template__study_id=study_id,
            deleted=False,
        ).select_related("definition", "ui_config", "section_template", "crf_template") \
         .prefetch_related("translations", "validation_rules__translations") \
         .first()

    def get_field_aggregate_by_scope(self, *, study_id, field_id):
        return (
            CrfFieldTemplate.objects.filter(
                pk=field_id,
                crf_template__study_id=study_id,
                deleted=False,
            )
            .select_related("definition", "ui_config", "section_template", "crf_template")
            .prefetch_related("translations", "validation_rules__translations")
            .first()
        )

    def exists_field_key(self, *, form_id, field_key, exclude_field_id=None):
        queryset = CrfFieldTemplate.objects.filter(
            crf_template_id=form_id,
            field_key=field_key,
            deleted=False,
        )
        if exclude_field_id:
            queryset = queryset.exclude(pk=exclude_field_id)
        return queryset.exists()

    def list_field_keys_for_form(self, *, form_id, exclude_field_id=None):
        queryset = CrfFieldTemplate.objects.filter(
            crf_template_id=form_id,
            deleted=False,
        ).values_list("field_key", flat=True)
        if exclude_field_id:
            queryset = queryset.exclude(pk=exclude_field_id)
        return tuple(queryset)

    def create_field_aggregate(self, *, form_id, aggregate, actor_user_id):
        now = timezone.now()
        field = CrfFieldTemplate(
            crf_template_id=form_id,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
            deleted=False,
        )
        self._apply_field_snapshot(field, aggregate.to_persistence_payload()["field_template"], now=now)
        field.save()

        self._save_definition_snapshot(field_template_id=field.pk, snapshot=aggregate.to_persistence_payload()["field_definition"], actor_user_id=actor_user_id, now=now)
        self._save_ui_config_snapshot(field_template_id=field.pk, snapshot=aggregate.to_persistence_payload()["field_ui_config"], actor_user_id=actor_user_id, now=now)
        validation_rules = self._replace_validation_rules(
            field_template_id=field.pk,
            snapshots=aggregate.to_persistence_payload()["field_validation_rules"],
            actor_user_id=actor_user_id,
            now=now,
        )

        return field, validation_rules

    def update_field_aggregate(self, *, aggregate, existing_field, actor_user_id):
        now = timezone.now()
        snapshot = aggregate.to_persistence_payload()
        self._apply_field_snapshot(existing_field, snapshot["field_template"], now=now, actor_user_id=actor_user_id)
        existing_field.save()

        self._save_definition_snapshot(
            field_template_id=existing_field.pk,
            snapshot=snapshot["field_definition"],
            actor_user_id=actor_user_id,
            now=now,
        )
        self._save_ui_config_snapshot(
            field_template_id=existing_field.pk,
            snapshot=snapshot["field_ui_config"],
            actor_user_id=actor_user_id,
            now=now,
        )
        validation_rules = self._replace_validation_rules(
            field_template_id=existing_field.pk,
            snapshots=snapshot["field_validation_rules"],
            actor_user_id=actor_user_id,
            now=now,
        )

        return existing_field, validation_rules

    def save_field_aggregate(self, *, form_id, field_id, aggregate, actor_user_id):
        now = timezone.now()
        snapshot = aggregate.to_persistence_payload()

        if field_id:
            field = CrfFieldTemplate.objects.filter(
                pk=field_id,
                crf_template_id=form_id,
                deleted=False,
            ).first()
            action = "updated"
        else:
            field = CrfFieldTemplate(
                crf_template_id=form_id,
                created_at=now,
                created_by_id=actor_user_id,
                deleted=False,
            )
            action = "created"

        self._apply_field_snapshot(field, snapshot["field_template"], now=now, actor_user_id=actor_user_id)
        field.save()

        self._save_definition_snapshot(
            field_template_id=field.pk,
            snapshot=snapshot["field_definition"],
            actor_user_id=actor_user_id,
            now=now,
        )
        self._save_ui_config_snapshot(
            field_template_id=field.pk,
            snapshot=snapshot["field_ui_config"],
            actor_user_id=actor_user_id,
            now=now,
        )
        validation_rules = self._replace_validation_rules(
            field_template_id=field.pk,
            snapshots=snapshot["field_validation_rules"],
            actor_user_id=actor_user_id,
            now=now,
        )

        return action, field

    def delete_field_aggregate(self, *, study_id, form_id, field_id, actor_user_id):
        now = timezone.now()
        field = CrfFieldTemplate.objects.filter(
            pk=field_id,
            crf_template_id=form_id,
            crf_template__study_id=study_id,
            deleted=False,
        ).select_related("definition", "ui_config").prefetch_related("validation_rules__translations").first()
        if field is None:
            return None

        self._soft_delete_field_models(field, now=now, actor_user_id=actor_user_id)
        return field

    def delete_section_template(self, *, study_id, form_id, section_id, actor_user_id):
        now = timezone.now()
        section = CrfSectionTemplate.objects.filter(
            pk=section_id,
            crf_template_id=form_id,
            crf_template__study_id=study_id,
            deleted=False,
        ).select_related("crf_template").prefetch_related("field_templates__definition", "field_templates__ui_config", "field_templates__validation_rules__translations").first()
        if section is None:
            return None

        for field in section.field_templates.all():
            if field.deleted:
                continue
            self._soft_delete_field_models(field, now=now, actor_user_id=actor_user_id)

        layout_config = getattr(section, "layout_config", None)
        if layout_config is not None and not layout_config.deleted:
            layout_config.deleted = True
            layout_config.updated_at = now
            layout_config.updated_by_id = actor_user_id
            layout_config.save(update_fields=["deleted", "updated_at", "updated_by_id"])

        section.deleted = True
        section.updated_at = now
        section.updated_by_id = actor_user_id
        section.save(update_fields=["deleted", "updated_at", "updated_by_id"])
        return section

    def _apply_field_snapshot(self, field, snapshot, *, now, actor_user_id=None):
        field.field_key = snapshot["field_key"]
        field.data_type = snapshot["data_type"]
        field.is_active = snapshot["is_active"]
        field.display_order = snapshot["display_order"]
        field.section_template_id = snapshot["section_template_id"]
        field.deleted = False
        field.updated_at = now
        if actor_user_id is not None:
            field.updated_by_id = actor_user_id

        field.set_current_language("en", initialize=True)
        field.label = snapshot["label_en"] or snapshot["field_key"]
        field.set_current_language("vi", initialize=True)
        field.label = snapshot["label_vi"] or snapshot["label_en"] or snapshot["field_key"]

    def _soft_delete_field_models(self, field, *, now, actor_user_id):
        definition = getattr(field, "definition", None)
        ui_config = getattr(field, "ui_config", None)
        validation_rules = list(getattr(field, "validation_rules", []).all()) if hasattr(field, "validation_rules") else []

        if definition is not None and not definition.deleted:
            definition.deleted = True
            definition.updated_at = now
            definition.updated_by_id = actor_user_id
            definition.save(update_fields=["deleted", "updated_at", "updated_by_id"])

        if ui_config is not None and not ui_config.deleted:
            ui_config.deleted = True
            ui_config.updated_at = now
            ui_config.updated_by_id = actor_user_id
            ui_config.save(update_fields=["deleted", "updated_at", "updated_by_id"])

        for validation_rule in validation_rules:
            if validation_rule.deleted:
                continue
            validation_rule.deleted = True
            validation_rule.updated_at = now
            validation_rule.updated_by_id = actor_user_id
            validation_rule.save(update_fields=["deleted", "updated_at", "updated_by_id"])

        field.deleted = True
        field.updated_at = now
        field.updated_by_id = actor_user_id
        field.save(update_fields=["deleted", "updated_at", "updated_by_id"])

    def _save_definition_snapshot(self, *, field_template_id, snapshot, actor_user_id, now):
        CrfFieldDefinition.objects.update_or_create(
            field_template_id=field_template_id,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "sdtm": json.dumps(snapshot["sdtm"], ensure_ascii=True, sort_keys=True),
                "unit": snapshot["unit"],
                "range_min": snapshot["range_min"],
                "range_max": snapshot["range_max"],
                "precision": snapshot["precision"],
                "allowed_missing_values": snapshot["allowed_missing_values"],
                "codelist": snapshot["codelist"] or "",
                "data_semantic": snapshot["data_semantic"],
                "comments": snapshot["comments"],
                "text_max_length": snapshot["text_max_length"],
                "text_min_length": snapshot["text_min_length"],
                "pattern": snapshot["pattern"],
                "pattern_err_msg": snapshot["pattern_err_msg"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )

    def _save_ui_config_snapshot(self, *, field_template_id, snapshot, actor_user_id, now):
        CrfFieldUiConfig.objects.update_or_create(
            field_template_id=field_template_id,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "control_type": snapshot["control_type"],
                "layout": snapshot["layout"],
                "text": snapshot["text"],
                "behavior": snapshot["behavior"],
                "options": snapshot["options"],
                "style": snapshot["style"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )

    def _replace_validation_rules(self, *, field_template_id, snapshots, actor_user_id, now):
        existing_rules = list(
            CrfFieldValidationRule.objects.filter(field_template_id=field_template_id)
            .prefetch_related("translations")
        )
        for validation_rule in existing_rules:
            validation_rule.delete()

        created_rules = []
        for snapshot in snapshots:
            validation_rule = CrfFieldValidationRule(
                field_template_id=field_template_id,
                created_at=now,
                updated_at=now,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
                deleted=False,
                rule_type=snapshot["rule_type"],
                expression=snapshot["expression"],
                severity=snapshot["severity"],
                mode=snapshot["mode"],
            )
            validation_rule.save()

            for translation in snapshot["translations"]:
                validation_rule.set_current_language(translation["language_code"], initialize=True)
                validation_rule.message = translation["message"]
                validation_rule.save()

            created_rules.append(validation_rule)

        return created_rules

    def get_form_with_translations(self, *, study_id, form_id):
        return CrfTemplate.objects.filter(
            pk=form_id,
            study_id=study_id,
            deleted=False,
        ).prefetch_related("translations").first()

    def get_form_builder_aggregate(self, *, form_id):
        validation_rules_qs = (
            CrfFieldValidationRule.objects.filter(deleted=False)
            .prefetch_related("translations")
            .order_by("pk")
        )
        section_templates_qs = (
            CrfSectionTemplate.objects.filter(deleted=False)
            .prefetch_related("translations")
            .order_by("display_order", "id")
        )
        field_templates_qs = (
            CrfFieldTemplate.objects.filter(deleted=False)
            .select_related("definition", "ui_config", "section_template")
            .prefetch_related("translations", Prefetch("validation_rules", queryset=validation_rules_qs))
            .order_by("display_order", "id")
        )

        return (
            CrfTemplate.objects.filter(
                pk=form_id,
                deleted=False,
            )
            .select_related("study")
            .prefetch_related(
                "translations",
                Prefetch("field_templates", queryset=field_templates_qs),
                Prefetch("section_templates", queryset=section_templates_qs),
            )
            .first()
        )

    def list_fields_for_form(self, *, form_id):
        return list(
            CrfFieldTemplate.objects.filter(
                crf_template_id=form_id,
                deleted=False,
            )
            .select_related("definition", "ui_config")
            .prefetch_related("translations", "validation_rules__translations")
            .order_by("display_order", "id")
        )
