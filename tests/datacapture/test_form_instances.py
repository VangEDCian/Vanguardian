from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.datacapture.application.services.form_instances import DataCaptureFormInstanceService


class TestDataCaptureFormInstanceService(SimpleTestCase):
    def test_to_instance_dto_uses_fallback_label_when_display_config_is_missing(self):
        list_field_schema = Mock(side_effect=AssertionError("schema should not be loaded"))
        render_label = Mock(side_effect=AssertionError("custom label renderer should not be used"))
        render_fallback_label = Mock(return_value="ConMed #2")
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(
                list_template_field_schema_for_display_label=list_field_schema,
            ),
            config_reader=SimpleNamespace(get_config=lambda binding_id: None),
            label_renderer=SimpleNamespace(
                render_label=render_label,
                render_fallback_label=render_fallback_label,
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(get_binding_snapshot=lambda **kwargs: None),
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: page_state),
        )
        page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=2,
            event_form_binding_id=45,
            crf_template_id=12,
            status="in_progress",
            final_data='{"MED_NAME":"Paracetamol"}',
            current_entry=None,
            event_form_binding=SimpleNamespace(
                pk=45,
                form_definition=SimpleNamespace(
                    code="CONMED",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "ConMed",
                ),
            ),
        )

        dto = service._to_instance_dto(page_state=page_state, language_code="en")

        self.assertEqual(dto.display_label, "ConMed #2")
        list_field_schema.assert_not_called()
        render_label.assert_not_called()
        render_fallback_label.assert_called_once_with(form_name="ConMed", repeat_index=2)

    def test_to_instance_dto_uses_preloaded_display_config_without_reader_lookup(self):
        get_config = Mock(side_effect=AssertionError("config reader should not be used"))
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(),
            config_reader=SimpleNamespace(get_config=get_config),
            label_renderer=SimpleNamespace(
                render_fallback_label=lambda **kwargs: "ConMed",
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(get_binding_snapshot=lambda **kwargs: None),
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: page_state),
        )
        page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=1,
            event_form_binding_id=45,
            crf_template_id=12,
            status="in_progress",
            final_data='{"MED_NAME":"Paracetamol"}',
            current_entry=None,
            event_form_binding=SimpleNamespace(
                pk=45,
                display_config=SimpleNamespace(is_enabled=False, deleted=False, use_choice_display_label=True),
                form_definition=SimpleNamespace(
                    code="CONMED",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "ConMed",
                ),
            ),
        )

        dto = service._to_instance_dto(page_state=page_state, language_code="en")

        self.assertEqual(dto.display_label, "ConMed")
        get_config.assert_not_called()

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
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: page_state),
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

    def test_to_instance_dto_prefers_snapshot_renderer_when_available(self):
        config = SimpleNamespace(is_enabled=True, use_choice_display_label=False)
        render_label = Mock(side_effect=AssertionError("binding renderer should not be used"))
        render_label_from_snapshot = Mock(return_value="ConMed #2 — Paracetamol")
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(
                list_template_field_schema_for_display_label=lambda template_id: [
                    {"field_key": "MED_NAME", "label": "Medication", "data_type": "TEXT", "ui_config": {}}
                ],
            ),
            config_reader=SimpleNamespace(get_config=lambda binding_id: config),
            label_renderer=SimpleNamespace(
                render_label=render_label,
                render_label_from_snapshot=render_label_from_snapshot,
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(get_binding_snapshot=lambda **kwargs: None),
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: page_state),
        )
        page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=2,
            event_form_binding_id=45,
            crf_template_id=12,
            status="in_progress",
            final_data='{"MED_NAME":"Paracetamol"}',
            current_entry=None,
            event_form_binding=SimpleNamespace(
                pk=45,
                form_definition=SimpleNamespace(
                    code="CONMED",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "ConMed",
                ),
            ),
        )

        dto = service._to_instance_dto(page_state=page_state, language_code="en")

        self.assertEqual(dto.display_label, "ConMed #2 — Paracetamol")
        render_label.assert_not_called()
        render_label_from_snapshot.assert_called_once_with(
            snapshot=config,
            language_code="en",
            repeat_index=2,
            field_values={"MED_NAME": "Paracetamol"},
        )

    def test_list_form_instances_heals_missing_binding_context_before_rendering(self):
        bound_page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=1,
            event_form_binding_id=45,
            crf_template_id=12,
            status="submitted",
            final_data="{}",
            current_entry=SimpleNamespace(data='{"MED_NAME":"Paracetamol"}'),
            event_form_binding=SimpleNamespace(
                pk=45,
                display_order=2,
                deleted=False,
                is_enabled=True,
                form_definition=SimpleNamespace(
                    code="CONMED",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "ConMed",
                ),
            ),
        )
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
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: bound_page_state),
        )

        class _FakeQuerySet(list):
            def select_related(self, *args, **kwargs):
                return self

            def prefetch_related(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return self[0] if self else None

        missing_binding_page_state = SimpleNamespace(
            pk=91,
            event_form_binding_id=None,
            crf_template_id=12,
            visit_id=76,
            repeat_index=1,
            current_entry=SimpleNamespace(data='{"MED_NAME":"Paracetamol"}'),
        )

        with (
            patch(
                "apps.datacapture.application.services.form_instances.get_event_instance_snapshot",
                return_value={
                    "id": 76,
                    "subject_id": 3,
                    "study_id": 1,
                    "event_definition_id": 17,
                    "repeat_index": 1,
                    "updated_at": "now",
                },
            ),
            patch(
                "apps.datacapture.application.services.form_instances.DataCapturePageState.objects.filter",
                return_value=_FakeQuerySet([missing_binding_page_state]),
            ),
        ):
            rows = service.list_form_instances_for_event_instance(visit_id=76, language_code="en")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].display_label, "ConMed #1 — Paracetamol")

    def test_list_form_instances_prefers_event_repeat_index_for_single_binding_instance(self):
        bound_page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=1,
            event_form_binding_id=45,
            crf_template_id=12,
            status="submitted",
            final_data="{}",
            current_entry=SimpleNamespace(data='{"AE_TERM":"Headache"}'),
            event_form_binding=SimpleNamespace(
                pk=45,
                display_order=2,
                deleted=False,
                is_enabled=True,
                form_definition=SimpleNamespace(
                    code="AE",
                    safe_translation_getter=lambda field_name, default="", language_code=None, any_language=False: "AE",
                ),
            ),
        )
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(
                list_template_field_schema_for_display_label=lambda template_id: [
                    {"field_key": "AE_TERM", "label": "AE Term", "data_type": "TEXT", "ui_config": {}}
                ],
                resolve_choice_display_label=lambda **kwargs: kwargs["raw_value"],
            ),
            config_reader=SimpleNamespace(
                get_config=lambda binding_id: SimpleNamespace(use_choice_display_label=True)
            ),
            label_renderer=SimpleNamespace(
                render_label=lambda **kwargs: f"AE #{kwargs['repeat_index']} — {kwargs['field_values']['AE_TERM']}"
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(get_binding_snapshot=lambda **kwargs: None),
            repository=SimpleNamespace(ensure_page_state_binding_context=lambda page_state, **kwargs: bound_page_state),
        )

        class _FakeQuerySet(list):
            def select_related(self, *args, **kwargs):
                return self

            def prefetch_related(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return self[0] if self else None

        with (
            patch(
                "apps.datacapture.application.services.form_instances.get_event_instance_snapshot",
                return_value={
                    "id": 83,
                    "subject_id": 3,
                    "study_id": 1,
                    "event_definition_id": 17,
                    "repeat_index": 2,
                    "updated_at": "now",
                },
            ),
            patch(
                "apps.datacapture.application.services.form_instances.DataCapturePageState.objects.filter",
                return_value=_FakeQuerySet([bound_page_state]),
            ),
        ):
            rows = service.list_form_instances_for_event_instance(visit_id=83, language_code="en")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].repeat_index, 2)
        self.assertEqual(rows[0].display_label, "AE #2 — Headache")

    def test_create_form_instance_for_non_repeatable_binding_uses_event_repeat_index(self):
        service = DataCaptureFormInstanceService(
            crf_context_adapter=SimpleNamespace(),
            config_reader=SimpleNamespace(get_config=lambda binding_id: None),
            label_renderer=SimpleNamespace(
                render_label=lambda **kwargs: f"AE #{kwargs['repeat_index']} — {kwargs['field_values'].get('AE_TERM', '')}"
            ),
            audit_context_adapter=SimpleNamespace(record_event=lambda **kwargs: None),
            binding_reader=SimpleNamespace(
                get_binding_snapshot=lambda **kwargs: {
                    "id": 45,
                    "study_id": 9,
                    "event_definition_id": 17,
                    "form_definition_id": 12,
                    "is_repeatable_within_event": False,
                }
            ),
            repository=SimpleNamespace(),
        )

        class _FakeQuerySet(list):
            def select_for_update(self):
                return self

            def filter(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

        created_page_state = SimpleNamespace(
            pk=91,
            instance_key="abc123",
            repeat_index=2,
            event_form_binding_id=45,
            crf_template_id=12,
            status="not_started",
            current_entry=None,
            final_data="{}",
        )

        with (
            patch(
                "apps.datacapture.application.services.form_instances.get_event_instance_snapshot",
                return_value={
                    "id": 76,
                    "subject_id": 3,
                    "study_id": 9,
                    "event_definition_id": 17,
                    "repeat_index": 2,
                    "updated_at": "now",
                },
            ),
            patch(
                "apps.datacapture.application.services.form_instances.DataCapturePageState.objects",
            ) as page_state_objects,
            patch(
                "apps.datacapture.application.services.form_instances.DataCapturePageStateTransitionLog.objects.create"
            ),
            patch.object(
                DataCaptureFormInstanceService,
                "_to_instance_dto",
                return_value=SimpleNamespace(repeat_index=2, display_label="AE #2 —", page_state_id=91),
            ),
        ):
            page_state_objects.select_for_update.return_value = _FakeQuerySet([])
            page_state_objects.create.return_value = created_page_state

            dto = DataCaptureFormInstanceService.create_form_instance.__wrapped__(
                service,
                subject_id=3,
                visit_id=76,
                event_form_binding_id=45,
                actor_user_id=1,
            )

        self.assertEqual(dto.repeat_index, 2)
        self.assertEqual(page_state_objects.create.call_args.kwargs["repeat_index"], 2)
