from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from django.test import SimpleTestCase

from apps.datacapture.application.services.fact_mapping_config import DataCaptureFactMappingConfigService
from apps.study.application.exceptions import FactMappingImportConflictError


class DataCaptureFactMappingConfigServiceTests(SimpleTestCase):
    @patch("apps.datacapture.application.services.fact_mapping_config.transaction.atomic")
    def test_upsert_fact_mapping_creates_missing_mapping(self, mock_atomic):
        mock_atomic.return_value = nullcontext()
        repository = MagicMock()
        repository.get_fact_mapping_for_import.return_value = None
        repository.create_fact_mapping.return_value = SimpleNamespace(pk=101)
        service = DataCaptureFactMappingConfigService(repository=repository)

        result = service.upsert_fact_mapping(
            study_id=3,
            study_version="v1.0",
            event_definition_id=61,
            crf_template_id=71,
            field_code="ELIGIBLE",
            source_path="ELIGIBLE",
            fact_key="screening.eligible",
            operator="is_true",
            expected_value=None,
            value_type="boolean",
            default_value="false",
            display_order=2,
            actor_user_id=99,
            now=ANY,
        )

        self.assertEqual(result.outcome, "created")
        self.assertEqual(result.fact_mapping_id, 101)
        repository.create_fact_mapping.assert_called_once_with(
            study_id=3,
            study_version="v1.0",
            event_definition_id=61,
            crf_template_id=71,
            fact_key="screening.eligible",
            created_at=ANY,
            created_by_id=99,
            field_code="ELIGIBLE",
            source_path="ELIGIBLE",
            operator="is_true",
            expected_value=None,
            value_type="boolean",
            default_value="false",
            is_enabled=True,
            display_order=2,
            deleted=False,
            updated_at=ANY,
            updated_by_id=99,
        )

    @patch("apps.datacapture.application.services.fact_mapping_config.transaction.atomic")
    def test_upsert_fact_mapping_updates_existing_mapping(self, mock_atomic):
        mock_atomic.return_value = nullcontext()
        repository = MagicMock()
        fact_mapping = SimpleNamespace(pk=102, crf_template_id=71)
        repository.get_fact_mapping_for_import.return_value = fact_mapping
        service = DataCaptureFactMappingConfigService(repository=repository)

        result = service.upsert_fact_mapping(
            study_id=3,
            study_version="v1.0",
            event_definition_id=61,
            crf_template_id=71,
            field_code=None,
            source_path="$.FORM.data.ELIGIBLE",
            fact_key="screening.eligible",
            operator="equals",
            expected_value="pass",
            value_type="string",
            default_value=None,
            display_order=1,
            actor_user_id=99,
            now=ANY,
        )

        self.assertEqual(result.outcome, "updated")
        self.assertEqual(fact_mapping.source_path, "$.FORM.data.ELIGIBLE")
        self.assertFalse(fact_mapping.deleted)
        repository.save_fact_mapping.assert_called_once()

    @patch("apps.datacapture.application.services.fact_mapping_config.transaction.atomic")
    def test_upsert_fact_mapping_rejects_conflicting_form_for_same_fact_key(self, mock_atomic):
        mock_atomic.return_value = nullcontext()
        repository = MagicMock()
        repository.get_fact_mapping_for_import.return_value = SimpleNamespace(pk=103, crf_template_id=72)
        service = DataCaptureFactMappingConfigService(repository=repository)

        with self.assertRaises(FactMappingImportConflictError):
            service.upsert_fact_mapping(
                study_id=3,
                study_version="v1.0",
                event_definition_id=61,
                crf_template_id=71,
                field_code=None,
                source_path="$.FORM.data.ELIGIBLE",
                fact_key="screening.eligible",
                operator="equals",
                expected_value="pass",
                value_type="string",
                default_value=None,
                display_order=1,
                actor_user_id=99,
                now=ANY,
            )
