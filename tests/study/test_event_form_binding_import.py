from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.shared.constants import EventFormEntryModeChoices
from apps.study.application.services.import_event_form_bindings_template import (
    ImportStudyEventFormBindingsTemplateService,
)


class ImportStudyEventFormBindingsTemplateServiceTests(SimpleTestCase):
    @patch.object(
        ImportStudyEventFormBindingsTemplateService,
        "_load_rows_from_workbook",
        return_value=[
            (
                2,
                {
                    "event_code": "SCREENING",
                    "form_code": "AE",
                    "display_order": "1",
                    "repeatable": "false",
                    "role_scope": "INVESTIGATOR",
                    "entry_mode": "single",
                },
            )
        ],
    )
    @patch("apps.study.application.services.import_event_form_bindings_template.transaction.atomic", return_value=nullcontext())
    def test_execute_replaces_existing_bindings_for_target_event_before_importing(
        self,
        _mock_atomic,
        mock_load_rows,
    ):
        event_definition = SimpleNamespace(pk=17, study_version="v1")
        form_definition = SimpleNamespace(pk=23)
        repository = MagicMock()
        repository.get_event_form_binding.return_value = None
        crf_context_adapter = MagicMock()
        crf_context_adapter.resolve_unique_template_by_code.return_value = form_definition
        service = ImportStudyEventFormBindingsTemplateService(
            crf_context_adapter=crf_context_adapter,
            repository=repository,
        )
        service._resolve_event_definition = MagicMock(return_value=event_definition)

        result = service.execute(
            command=SimpleNamespace(
                actor_user_id=7,
                selected_study_id=3,
                study_id=3,
                file_name="event_form_bindings.xlsx",
                file_content=b"xlsx",
            )
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 0)
        self.assertEqual(result.skipped_count, 0)
        repository.soft_delete_event_form_bindings_for_import.assert_called_once_with(
            event_definition_ids=[17],
            actor_user_id=7,
            updated_at=repository.soft_delete_event_form_bindings_for_import.call_args.kwargs["updated_at"],
        )
        repository.create_event_form_binding.assert_called_once_with(
            event_definition_id=17,
            form_definition_id=23,
            created_at=repository.create_event_form_binding.call_args.kwargs["created_at"],
            created_by_id=7,
            study_id=3,
            study_version="v1",
            display_order=1,
            is_repeatable_within_event=False,
            role_scope="INVESTIGATOR",
            entry_mode=EventFormEntryModeChoices.SINGLE,
            is_required=True,
            is_enabled=True,
            deleted=False,
            updated_at=repository.create_event_form_binding.call_args.kwargs["updated_at"],
            updated_by_id=7,
        )
        mock_load_rows.assert_called_once()

    @patch.object(
        ImportStudyEventFormBindingsTemplateService,
        "_load_rows_from_workbook",
        return_value=[
            (
                2,
                {
                    "event_code": "SCREENING",
                    "form_code": "AE",
                    "display_order": "2",
                    "repeatable": "true",
                    "role_scope": "",
                    "entry_mode": "double entry",
                },
            )
        ],
    )
    @patch("apps.study.application.services.import_event_form_bindings_template.transaction.atomic", return_value=nullcontext())
    def test_execute_reactivates_binding_when_reset_import_updates_existing_row(
        self,
        _mock_atomic,
        mock_load_rows,
    ):
        event_definition = SimpleNamespace(pk=17, study_version="v1")
        form_definition = SimpleNamespace(pk=23)
        binding = SimpleNamespace()
        repository = MagicMock()
        repository.get_event_form_binding.return_value = binding
        crf_context_adapter = MagicMock()
        crf_context_adapter.resolve_unique_template_by_code.return_value = form_definition
        service = ImportStudyEventFormBindingsTemplateService(
            crf_context_adapter=crf_context_adapter,
            repository=repository,
        )
        service._resolve_event_definition = MagicMock(return_value=event_definition)

        result = service.execute(
            command=SimpleNamespace(
                actor_user_id=7,
                selected_study_id=3,
                study_id=3,
                file_name="event_form_bindings.xlsx",
                file_content=b"xlsx",
            )
        )

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(binding.study_id, 3)
        self.assertEqual(binding.study_version, "v1")
        self.assertEqual(binding.display_order, 2)
        self.assertTrue(binding.is_repeatable_within_event)
        self.assertIsNone(binding.role_scope)
        self.assertEqual(binding.entry_mode, "double_entry")
        self.assertTrue(binding.is_required)
        self.assertTrue(binding.is_enabled)
        self.assertFalse(binding.deleted)
        repository.save_event_form_binding.assert_called_once()
        update_fields = repository.save_event_form_binding.call_args.kwargs["update_fields"]
        self.assertIn("deleted", update_fields)
        self.assertIn("is_enabled", update_fields)
        self.assertIn("is_required", update_fields)
        mock_load_rows.assert_called_once()
