from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.crf.application.form_builder_audit import CrfFormBuilderAuditService
from apps.crf.domain import (
    FieldKeyExistsError,
    FieldScopeViolationError,
    FieldTemplateAggregate,
    FormBuilderDomainValidationError,
    FormScopeViolationError,
    StudyScopeViolationError,
)
from apps.crf.infrastructure.repositories import DjangoOrmFormBuilderRepository


@dataclass(frozen=True)
class SaveFieldAggregateCommand:
    selected_study_id: int
    study_id: int
    form_id: int
    actor_user_id: int
    ip_address: str | None
    user_agent: str
    field_id: int | None

    field_key: str
    data_type: str
    is_active: bool
    display_order: int
    section_template_id: int | None
    label_en: str
    label_vi: str

    definition: dict
    ui_config: dict
    validation_rules: list


@dataclass(frozen=True)
class CreateFieldAggregateCommand:
    selected_study_id: int
    study_id: int
    form_id: int
    actor_user_id: int
    ip_address: str | None
    user_agent: str

    field_key: str
    data_type: str
    is_active: bool
    display_order: int
    section_template_id: int | None
    label_en: str
    label_vi: str

    definition: dict
    ui_config: dict
    validation_rules: list


@dataclass(frozen=True)
class UpdateFieldAggregateCommand:
    selected_study_id: int
    study_id: int
    field_id: int
    actor_user_id: int
    ip_address: str | None
    user_agent: str

    field_key: str
    data_type: str
    is_active: bool
    display_order: int
    section_template_id: int | None
    label_en: str
    label_vi: str

    definition: dict
    ui_config: dict
    validation_rules: list


class FormBuilderOrchestrationService:
    repository_class = DjangoOrmFormBuilderRepository
    audit_service_class = CrfFormBuilderAuditService

    def __init__(self, repository=None, audit_service=None):
        self.repository = repository or self.repository_class()
        self.audit_service = audit_service or self.audit_service_class()

    @staticmethod
    def _normalize_selected_study_id(selected_study_id):
        if selected_study_id is None:
            raise StudyScopeViolationError("No study is selected in the current context.")
        return int(selected_study_id)

    @classmethod
    def _ensure_current_study_scope(cls, *, selected_study_id, study_id):
        selected_study_id = cls._normalize_selected_study_id(selected_study_id)
        if int(study_id) != selected_study_id:
            raise StudyScopeViolationError("Command study scope does not match the selected study.")
        return selected_study_id

    @staticmethod
    def _sanitize_for_audit(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: FormBuilderOrchestrationService._sanitize_for_audit(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [FormBuilderOrchestrationService._sanitize_for_audit(item) for item in value]
        return value

    def _aggregate_metadata_snapshot(self, aggregate):
        return self._sanitize_for_audit(aggregate.to_persistence_payload())

    def _model_metadata_snapshot(self, field):
        definition = getattr(field, "definition", None)
        ui_config = getattr(field, "ui_config", None)
        rules = list(field.validation_rules.all()) if hasattr(field, "validation_rules") else []

        return self._sanitize_for_audit(
            {
                "field_template": {
                    "field_key": field.field_key,
                    "data_type": field.data_type,
                    "is_active": bool(field.is_active),
                    "display_order": field.display_order,
                    "section_template_id": field.section_template_id,
                    "label_en": field.safe_translation_getter("label", default="", language_code="en") if hasattr(field, "safe_translation_getter") else "",
                    "label_vi": field.safe_translation_getter("label", default="", language_code="vi") if hasattr(field, "safe_translation_getter") else "",
                },
                "field_definition": {
                    "sdtm": getattr(definition, "sdtm", "") if definition else "",
                    "unit": getattr(definition, "unit", None) if definition else None,
                    "range_min": getattr(definition, "range_min", None) if definition else None,
                    "range_max": getattr(definition, "range_max", None) if definition else None,
                    "precision": getattr(definition, "precision", None) if definition else None,
                    "allowed_missing_values": getattr(definition, "allowed_missing_values", "") if definition else "",
                    "codelist": getattr(definition, "codelist", None) if definition else None,
                    "data_semantic": getattr(definition, "data_semantic", None) if definition else None,
                    "comments": getattr(definition, "comments", None) if definition else None,
                    "text_max_length": getattr(definition, "text_max_length", None) if definition else None,
                    "text_min_length": getattr(definition, "text_min_length", None) if definition else None,
                    "pattern": getattr(definition, "pattern", None) if definition else None,
                    "pattern_err_msg": getattr(definition, "pattern_err_msg", None) if definition else None,
                },
                "field_ui_config": {
                    "control_type": getattr(ui_config, "control_type", None) if ui_config else None,
                    "layout": getattr(ui_config, "layout", None) if ui_config else None,
                    "text": getattr(ui_config, "text", None) if ui_config else None,
                    "behavior": getattr(ui_config, "behavior", None) if ui_config else None,
                    "options": getattr(ui_config, "options", None) if ui_config else None,
                    "style": getattr(ui_config, "style", None) if ui_config else None,
                },
                "field_validation_rules": [
                    {
                        "id": rule.pk,
                        "rule_type": rule.rule_type,
                        "expression": rule.expression,
                        "severity": rule.severity,
                        "mode": rule.mode,
                        "translations": {
                            str(translation.language_code).strip().lower(): translation.message or ""
                            for translation in getattr(rule, "translations", []).all()
                        },
                    }
                    for rule in rules
                ],
            }
        )

    @transaction.atomic
    def save_field(self, *, command: SaveFieldAggregateCommand):
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        form = self.repository.get_form_by_scope(
            study_id=command.study_id,
            form_id=command.form_id,
        )
        if form is None:
            raise FormScopeViolationError("Form is not found in this study scope.")

        existing_field = None
        if command.field_id:
            existing_field = self.repository.get_field_by_scope(
                study_id=command.study_id,
                form_id=command.form_id,
                field_id=command.field_id,
            )
            if existing_field is None:
                raise FieldScopeViolationError("Field is not found in this form scope.")

        field_keys_in_form = self.repository.list_field_keys_for_form(
            form_id=command.form_id,
            exclude_field_id=command.field_id,
        )

        aggregate = FieldTemplateAggregate.from_payload(
            field_key=command.field_key,
            data_type=command.data_type,
            is_active=command.is_active,
            display_order=command.display_order,
            section_template_id=command.section_template_id,
            label_en=command.label_en,
            label_vi=command.label_vi,
            definition=command.definition,
            ui_config=command.ui_config,
            validation_rules=command.validation_rules,
            field_keys_in_form=field_keys_in_form,
        )

        action, field = self.repository.save_field_aggregate(
            form_id=command.form_id,
            field_id=command.field_id,
            aggregate=aggregate,
            actor_user_id=command.actor_user_id,
        )

        after_data = {
            "field_key": field.field_key,
            "data_type": field.data_type,
            "is_active": bool(field.is_active),
            "display_order": field.display_order,
            "metadata": self._aggregate_metadata_snapshot(aggregate),
        }
        if action == "created":
            self.audit_service.record_field_created(
                study_id=command.study_id,
                form_id=command.form_id,
                field_template_id=field.pk,
                after_data=after_data,
                actor_user_id=command.actor_user_id,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
            )
        else:
            before_data = {
                "field_key": existing_field.field_key,
                "data_type": existing_field.data_type,
                "is_active": bool(existing_field.is_active),
                "display_order": existing_field.display_order,
                "metadata": self._model_metadata_snapshot(existing_field),
            }
            self.audit_service.record_field_updated(
                study_id=command.study_id,
                form_id=command.form_id,
                field_template_id=field.pk,
                before_data=before_data,
                after_data=after_data,
                actor_user_id=command.actor_user_id,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
            )

        return {"action": action, "field_id": field.pk}

    @transaction.atomic
    def create_field(self, *, command: CreateFieldAggregateCommand):
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        form = self.repository.get_form_by_scope(
            study_id=command.study_id,
            form_id=command.form_id,
        )
        if form is None:
            raise StudyScopeViolationError("Form is not found in the selected study scope.")

        field_keys_in_form = self.repository.list_field_keys_for_form(
            form_id=command.form_id,
        )

        aggregate = FieldTemplateAggregate.from_payload(
            field_key=command.field_key,
            data_type=command.data_type,
            is_active=command.is_active,
            display_order=command.display_order,
            section_template_id=command.section_template_id,
            label_en=command.label_en,
            label_vi=command.label_vi,
            definition=command.definition,
            ui_config=command.ui_config,
            validation_rules=command.validation_rules,
            field_keys_in_form=field_keys_in_form,
        )

        field, validation_rules = self.repository.create_field_aggregate(
            form_id=command.form_id,
            aggregate=aggregate,
            actor_user_id=command.actor_user_id,
        )

        self.audit_service.record_field_created(
            study_id=command.study_id,
            form_id=command.form_id,
            field_template_id=field.pk,
            after_data={
                "field_key": field.field_key,
                "data_type": field.data_type,
                "is_active": bool(field.is_active),
                "display_order": field.display_order,
                "validation_rules_count": len(validation_rules),
                "metadata": self._aggregate_metadata_snapshot(aggregate),
            },
            actor_user_id=command.actor_user_id,
            ip_address=command.ip_address,
            user_agent=command.user_agent,
        )

        return {"action": "created", "field_id": field.pk}

    @transaction.atomic
    def update_field(self, *, command: UpdateFieldAggregateCommand):
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        existing_field = self.repository.get_field_aggregate_by_scope(
            study_id=command.study_id,
            field_id=command.field_id,
        )
        if existing_field is None:
            raise StudyScopeViolationError("Field is not found in the selected study scope.")

        field_keys_in_form = self.repository.list_field_keys_for_form(
            form_id=existing_field.crf_template_id,
            exclude_field_id=command.field_id,
        )

        aggregate = FieldTemplateAggregate.from_payload(
            field_key=command.field_key,
            data_type=command.data_type,
            is_active=command.is_active,
            display_order=command.display_order,
            section_template_id=command.section_template_id,
            label_en=command.label_en,
            label_vi=command.label_vi,
            definition=command.definition,
            ui_config=command.ui_config,
            validation_rules=command.validation_rules,
            field_keys_in_form=field_keys_in_form,
        )

        before_data = {
            "field_key": existing_field.field_key,
            "data_type": existing_field.data_type,
            "is_active": bool(existing_field.is_active),
            "display_order": existing_field.display_order,
            "metadata": self._model_metadata_snapshot(existing_field),
        }

        field, validation_rules = self.repository.update_field_aggregate(
            aggregate=aggregate,
            existing_field=existing_field,
            actor_user_id=command.actor_user_id,
        )

        self.audit_service.record_field_updated(
            study_id=command.study_id,
            form_id=existing_field.crf_template_id,
            field_template_id=field.pk,
            before_data=before_data,
            after_data={
                "field_key": field.field_key,
                "data_type": field.data_type,
                "is_active": bool(field.is_active),
                "display_order": field.display_order,
                "validation_rules_count": len(validation_rules),
                "metadata": self._aggregate_metadata_snapshot(aggregate),
            },
            actor_user_id=command.actor_user_id,
            ip_address=command.ip_address,
            user_agent=command.user_agent,
        )

        return {"action": "updated", "field_id": field.pk}


__all__ = [
    "SaveFieldAggregateCommand",
    "CreateFieldAggregateCommand",
    "UpdateFieldAggregateCommand",
    "FormBuilderOrchestrationService",
    "FieldKeyExistsError",
    "FieldScopeViolationError",
    "FormBuilderDomainValidationError",
    "FormScopeViolationError",
    "StudyScopeViolationError",
]
