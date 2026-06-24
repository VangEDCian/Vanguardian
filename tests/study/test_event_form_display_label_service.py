from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.services.event_form_display_label import (
    EventFormDisplayConfigSnapshot,
    EventFormDisplayLabelService,
    EventFormDisplayTranslationSnapshot,
)


class TestEventFormDisplayLabelService(SimpleTestCase):
    def setUp(self):
        self.binding = SimpleNamespace(
            pk=41,
            form_definition_id=12,
            form_definition=SimpleNamespace(
                code="AE",
                safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: (
                    "Adverse Event" if language_code == "en" else "Bien co bat loi"
                ),
            ),
        )
        self.service = EventFormDisplayLabelService()
        self.service._get_binding = lambda binding_id: self.binding
        self.service._allowed_field_keys = lambda template_id: {"AETERM", "SAETERM"}

    def test_validate_rejects_unknown_token(self):
        errors = self.service._validate_templates(
            label_template="{{unknown}}",
            fallback_template="{{form_name}} #{{repeat_index}}",
            allowed_field_keys={"AETERM"},
            max_length=120,
        )

        self.assertEqual(errors[0].code, "unsupported_token")

    def test_validate_rejects_field_key_outside_template(self):
        errors = self.service._validate_templates(
            label_template="{{field:CM_DRUG_NAME}}",
            fallback_template="{{form_name}} #{{repeat_index}}",
            allowed_field_keys={"AETERM"},
            max_length=120,
        )

        self.assertEqual(errors[0].code, "field_key_not_found")

    def test_preview_uses_fallback_when_all_field_tokens_are_empty(self):
        preview = self.service.preview(
            binding_id=41,
            language_code="en",
            label_template="AE #{{repeat_index}} — {{field:AETERM}}",
            fallback_template="{{form_name}} #{{repeat_index}}",
            empty_value_text="N/A",
            empty_value_policy="FALLBACK",
            max_length=120,
            repeat_index=2,
            field_values={},
        )

        self.assertEqual(preview.label, "Adverse Event #2")

    def test_render_label_falls_back_to_form_name_when_config_missing(self):
        self.service._build_snapshot = lambda binding: EventFormDisplayConfigSnapshot(
            binding_id=41,
            template_id=12,
            form_code="AE",
            form_name_by_language={"en": "Adverse Event", "vi": "Bien co bat loi"},
            is_enabled=False,
            syntax_version=1,
            max_length=120,
            use_choice_display_label=True,
            empty_value_policy="FALLBACK",
            translations={},
        )

        result = self.service.render_label(
            binding_id=41,
            language_code="en",
            repeat_index=3,
            field_values={"AETERM": "Headache"},
        )

        self.assertEqual(result, "Adverse Event #3")

    def test_render_label_fallback_does_not_append_hash_one_for_non_repeated_instance(self):
        self.service._build_snapshot = lambda binding: EventFormDisplayConfigSnapshot(
            binding_id=41,
            template_id=12,
            form_code="AE",
            form_name_by_language={"en": "Adverse Event", "vi": "Bien co bat loi"},
            is_enabled=False,
            syntax_version=1,
            max_length=120,
            use_choice_display_label=True,
            empty_value_policy="FALLBACK",
            translations={},
        )

        result = self.service.render_label(
            binding_id=41,
            language_code="en",
            repeat_index=1,
            field_values={},
        )

        self.assertEqual(result, "Adverse Event")

    def test_render_label_uses_empty_text_policy(self):
        self.service._build_snapshot = lambda binding: EventFormDisplayConfigSnapshot(
            binding_id=41,
            template_id=12,
            form_code="AE",
            form_name_by_language={"en": "Adverse Event", "vi": "Bien co bat loi"},
            is_enabled=True,
            syntax_version=1,
            max_length=120,
            use_choice_display_label=True,
            empty_value_policy="EMPTY_TEXT",
            translations={
                "en": EventFormDisplayTranslationSnapshot(
                    language_code="en",
                    label_template="AE #{{repeat_index}} — {{field:AETERM}}",
                    fallback_template="{{form_name}} #{{repeat_index}}",
                    empty_value_text="Pending",
                )
            },
        )

        result = self.service.render_label(
            binding_id=41,
            language_code="en",
            repeat_index=1,
            field_values={},
        )

        self.assertEqual(result, "AE #1 — Pending")

    def test_render_label_from_snapshot_does_not_reload_binding(self):
        snapshot = EventFormDisplayConfigSnapshot(
            binding_id=41,
            template_id=12,
            form_code="CM",
            form_name_by_language={"en": "ConMed", "vi": "Thuoc dung kem"},
            is_enabled=True,
            syntax_version=1,
            max_length=120,
            use_choice_display_label=True,
            empty_value_policy="FALLBACK",
            translations={
                "en": EventFormDisplayTranslationSnapshot(
                    language_code="en",
                    label_template="{{form_name}} #{{repeat_index}} — {{field:MED_NAME}}",
                    fallback_template="{{form_name}} #{{repeat_index}}",
                    empty_value_text="",
                )
            },
        )
        self.service._get_binding = lambda binding_id: (_ for _ in ()).throw(
            AssertionError("binding should not be reloaded")
        )

        result = self.service.render_label_from_snapshot(
            snapshot=snapshot,
            language_code="en",
            repeat_index=2,
            field_values={"MED_NAME": "Paracetamol"},
        )

        self.assertEqual(result, "ConMed #2 — Paracetamol")
