from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.datacapture.application.services.form_instances import DataCaptureFormInstanceService


class TestDataCaptureFormInstanceService(SimpleTestCase):
    def test_to_instance_dto_renders_display_label_from_current_entry_payload(self):
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(
                list_template_field_schema_for_display_label=lambda template_id: [
                    {"field_key": "MED_NAME", "label": "Medication", "data_type": "TEXT", "ui_config": {}}
                ],
                resolve_choice_display_label=lambda **kwargs: kwargs["raw_value"],
            ),
            config_reader=SimpleNamespace(
                get_config=lambda binding_id: SimpleNamespace(use_choice_display_label=True)
            ),
            label_renderer=SimpleNamespace(
                render_label=lambda **kwargs: f"ConMed #{kwargs['repeat_index']} — {kwargs['field_values']['MED_NAME']}"
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(get_binding_snapshot=lambda **kwargs: None),
        )
        page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=2,
            event_form_binding_id=45,
            crf_template_id=12,
            status="in_progress",
            final_data="{}",
            current_entry=SimpleNamespace(data='{"MED_NAME":"Paracetamol"}'),
            event_form_binding=SimpleNamespace(
                pk=45,
                form_definition=SimpleNamespace(
                    code="CONMED",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "ConMed",
                ),
            ),
        )

        dto = service._to_instance_dto(page_state=page_state, language_code="en")

        self.assertEqual(dto.page_state_id, 91)
        self.assertEqual(dto.repeat_index, 2)
        self.assertEqual(dto.display_label, "ConMed #2 — Paracetamol")
