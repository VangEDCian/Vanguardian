from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from django.db import transaction
from django.utils.translation import get_language

from apps.audit.public import AuditContextAdapter
from apps.core.choices import DataCapturePageStateStatusChoices
from apps.core.form_data_document import flatten_form_data_for_export, normalize_form_data
from apps.crf.public import CrfContextAdapter
from apps.datacapture.infrastructure.persistence.models import (
    DataCapturePageState,
    DataCapturePageStateTransitionLog,
)
from apps.shared.constants import AuditEventActionEnum, AuditEventObjectTypeEnum
from apps.study.public import (
    EventFormDisplayConfigReader,
    EventFormDisplayLabelRenderer,
    StudyEventFormBindingReader,
)
from apps.subject.public import get_event_instance_snapshot


@dataclass(frozen=True)
class DataCaptureFormInstanceDTO:
    page_state_id: int
    instance_key: str
    repeat_index: int
    event_form_binding_id: int
    crf_template_id: int
    template_name: str
    display_label: str
    status: str


class DataCaptureFormInstanceService:
    crf_context_adapter_class = CrfContextAdapter
    config_reader_class = EventFormDisplayConfigReader
    label_renderer_class = EventFormDisplayLabelRenderer
    audit_context_adapter_class = AuditContextAdapter
    binding_reader_class = StudyEventFormBindingReader

    def __init__(
        self,
        *,
        crf_context_adapter=None,
        config_reader=None,
        label_renderer=None,
        audit_context_adapter=None,
        binding_reader=None,
    ):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()
        self.config_reader = config_reader or self.config_reader_class()
        self.label_renderer = label_renderer or self.label_renderer_class()
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()
        self.binding_reader = binding_reader or self.binding_reader_class()

    @transaction.atomic
    def create_form_instance(
        self,
        *,
        subject_id: int,
        visit_id: int,
        event_form_binding_id: int,
        actor_user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> DataCaptureFormInstanceDTO:
        binding = self.binding_reader.get_binding_snapshot(binding_id=event_form_binding_id)
        if binding is None:
            raise ValueError("Event form binding was not found.")
        visit = get_event_instance_snapshot(event_instance_id=visit_id)
        if visit is None:
            raise ValueError("Subject event instance was not found.")
        if int(visit["subject_id"]) != int(subject_id):
            raise ValueError("Visit does not belong to the subject.")
        if int(visit["event_definition_id"]) != int(binding["event_definition_id"]):
            raise ValueError("Binding does not belong to the visit event definition.")
        if int(visit["study_id"]) != int(binding["study_id"]):
            raise ValueError("Binding does not belong to the visit study.")

        existing_states = list(
            DataCapturePageState.objects.select_for_update()
            .filter(
                subject_id=subject_id,
                visit_id=visit_id,
                event_form_binding_id=event_form_binding_id,
                deleted=False,
            )
            .order_by("repeat_index", "id")
        )
        if not binding["is_repeatable_within_event"] and existing_states:
            raise ValueError("This event form binding is not repeatable within the visit.")
        next_repeat_index = (
            max((int(page_state.repeat_index or 0) for page_state in existing_states), default=0) + 1
        )
        page_state = DataCapturePageState.objects.create(
            created_at=visit["updated_at"],
            updated_at=visit["updated_at"],
            deleted=False,
            status=DataCapturePageStateStatusChoices.NOT_STARTED,
            final_data="{}",
            data_version=1,
            crf_template_id=binding["form_definition_id"],
            event_form_binding_id=event_form_binding_id,
            repeat_index=next_repeat_index,
            instance_key=uuid4().hex,
            subject_id=subject_id,
            visit_id=visit_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        DataCapturePageStateTransitionLog.objects.create(
            created_at=visit["updated_at"],
            page_state=page_state,
            from_status=None,
            to_status=DataCapturePageStateStatusChoices.NOT_STARTED,
            data_version=1,
            reason_code="instance_created",
            reason_text="repeated_form_instance_created",
            trigger_source="create_form_instance",
            actor_id=actor_user_id,
            facts_json="{}",
        )
        dto = self._to_instance_dto(page_state=page_state, language_code=self._language_code())
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.DATACAPTURE_FORM_INSTANCE_CREATED,
            object_type=AuditEventObjectTypeEnum.DATACAPTURE_FORM_INSTANCE,
            object_id=str(page_state.pk),
            before_data={},
            after_data={
                "page_state_id": page_state.pk,
                "event_form_binding_id": event_form_binding_id,
                "repeat_index": next_repeat_index,
                "instance_key": page_state.instance_key,
                "subject_id": subject_id,
                "visit_id": visit_id,
            },
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent or "",
        )
        return dto

    def list_form_instances_for_event_instance(
        self,
        *,
        visit_id: int,
        language_code: str | None = None,
    ) -> list[DataCaptureFormInstanceDTO]:
        page_states = list(
            DataCapturePageState.objects.filter(
                visit_id=visit_id,
                deleted=False,
                event_form_binding__deleted=False,
                event_form_binding__is_enabled=True,
            )
            .select_related("event_form_binding", "event_form_binding__form_definition", "current_entry")
            .prefetch_related("event_form_binding__form_definition__translations")
            .order_by("event_form_binding__display_order", "repeat_index", "id")
        )
        normalized_language = self._language_code(language_code)
        return [
            self._to_instance_dto(page_state=page_state, language_code=normalized_language)
            for page_state in page_states
        ]

    def _to_instance_dto(
        self,
        *,
        page_state: DataCapturePageState,
        language_code: str,
    ) -> DataCaptureFormInstanceDTO:
        binding = page_state.event_form_binding
        template_name = self._template_name(binding=binding, language_code=language_code)
        config = self.config_reader.get_config(binding_id=int(binding.pk))
        field_values = self._display_field_values(
            page_state=page_state,
            language_code=language_code,
            use_choice_display_label=(
                True if config is None else bool(config.use_choice_display_label)
            ),
        )
        display_label = self.label_renderer.render_label(
            binding_id=int(binding.pk),
            language_code=language_code,
            repeat_index=int(page_state.repeat_index or 1),
            field_values=field_values,
        )
        return DataCaptureFormInstanceDTO(
            page_state_id=int(page_state.pk),
            instance_key=str(page_state.instance_key or ""),
            repeat_index=int(page_state.repeat_index or 1),
            event_form_binding_id=int(page_state.event_form_binding_id),
            crf_template_id=int(page_state.crf_template_id),
            template_name=template_name,
            display_label=display_label,
            status=str(page_state.status),
        )

    def _display_field_values(
        self,
        *,
        page_state: DataCapturePageState,
        language_code: str,
        use_choice_display_label: bool,
    ) -> dict[str, str]:
        raw_payload = "{}"
        current_entry = getattr(page_state, "current_entry", None)
        if current_entry is not None and getattr(current_entry, "data", ""):
            raw_payload = current_entry.data
        elif getattr(page_state, "final_data", ""):
            raw_payload = page_state.final_data
        try:
            parsed = json.loads(raw_payload or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = {}
        doc = normalize_form_data(parsed if isinstance(parsed, dict) else {}, strict=False)
        flattened = flatten_form_data_for_export(doc, repeat_strategy="legacy_repeat_suffix")
        schema = self.crf_context_adapter.list_template_field_schema_for_display_label(
            template_id=page_state.crf_template_id,
        )
        payload: dict[str, str] = {}
        for field in schema:
            field_key = str(field["field_key"])
            raw_value = flattened.get(field_key, "")
            normalized_value = "" if raw_value is None else str(raw_value)
            if not normalized_value:
                continue
            if use_choice_display_label:
                normalized_value = self.crf_context_adapter.resolve_choice_display_label(
                    template_id=page_state.crf_template_id,
                    field_key=field_key,
                    raw_value=normalized_value,
                    language_code=language_code,
                )
            payload[field_key] = normalized_value
        return payload

    def _template_name(self, *, binding, language_code: str) -> str:
        form_definition = binding.form_definition
        if hasattr(form_definition, "safe_translation_getter"):
            value = form_definition.safe_translation_getter(
                "name",
                default=form_definition.code,
                language_code=language_code,
                any_language=True,
            )
            return str(value or form_definition.code)
        return str(form_definition.code)

    @staticmethod
    def _language_code(language_code: str | None = None) -> str:
        normalized = (language_code or get_language() or "en").strip().lower()
        return normalized.split("-", 1)[0]


__all__ = [
    "DataCaptureFormInstanceDTO",
    "DataCaptureFormInstanceService",
]
