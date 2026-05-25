from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.datacapture.infrastructure.repositories.fact_mapping import DjangoDataCaptureFactMappingRepository


class DjangoDataCaptureFactMappingRepositoryTests(SimpleTestCase):
    def test_build_fact_source_uses_form_code_status_final_data_and_open_query_counts(self):
        repository = DjangoDataCaptureFactMappingRepository()
        page_states = [
            SimpleNamespace(
                pk=11,
                crf_template_id=101,
                crf_template=SimpleNamespace(code="SCREENING_DEMOGRAPHICS"),
                status="submitted",
                final_data='{"format":"edc.form_data.v1","groups":{"DEMOGRAPHICS":{"kind":"single","items":{"AGE":"900"}}}}',
            ),
            SimpleNamespace(
                pk=12,
                crf_template_id=102,
                crf_template=SimpleNamespace(code="SCREENING_INCLUSION_CRITERIA"),
                status="verified",
                final_data='{"format":"edc.form_data.v1","groups":{"INCLUSION":{"kind":"single","items":{"ELIGIBLE":true}}}}',
            ),
        ]

        fact_source = repository._build_fact_source_from_page_states(
            page_states=page_states,
            current_page_state_id=11,
            open_query_counts_by_page_state_id={11: 10},
        )

        self.assertEqual(fact_source.current_form_code, "SCREENING_DEMOGRAPHICS")
        self.assertEqual(
            fact_source.to_jsonpath_context(),
            {
                "SCREENING_DEMOGRAPHICS": {
                    "data": {
                        "format": "edc.form_data.v1",
                        "groups": {
                            "DEMOGRAPHICS": {
                                "kind": "single",
                                "items": {"AGE": "900"},
                            }
                        },
                    },
                    "status": "submitted",
                    "open_queries": 10,
                },
                "SCREENING_INCLUSION_CRITERIA": {
                    "data": {
                        "format": "edc.form_data.v1",
                        "groups": {
                            "INCLUSION": {
                                "kind": "single",
                                "items": {"ELIGIBLE": True},
                            }
                        },
                    },
                    "status": "verified",
                    "open_queries": 0,
                },
            },
        )

    def test_count_open_queries_by_page_state_ids_reads_reconcile_open_status(self):
        repository = DjangoDataCaptureFactMappingRepository()

        with patch("apps.datacapture.infrastructure.repositories.fact_mapping.ReconcileDataQuery.objects") as objects:
            objects.filter.return_value.values.return_value.annotate.return_value = [
                {"page_state_id": 11, "open_query_count": 10},
                {"page_state_id": 12, "open_query_count": 1},
            ]

            result = repository._count_open_queries_by_page_state_ids(page_state_ids=[11, 12])

        objects.filter.assert_called_once_with(
            page_state_id__in=[11, 12],
            deleted=False,
            status="open",
        )
        self.assertEqual(result, {11: 10, 12: 1})
