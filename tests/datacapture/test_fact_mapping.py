import json

from django.test import SimpleTestCase

from apps.datacapture.domain import (
    DataCaptureFactForm,
    DataCaptureFactMappingEvaluator,
    DataCaptureFactMappingRule,
    DataCaptureFactSource,
)


class DataCaptureFactMappingEvaluatorTests(SimpleTestCase):
    def setUp(self):
        self.evaluator = DataCaptureFactMappingEvaluator()

    def test_build_facts_maps_flat_final_data_to_fact_booleans(self):
        final_data = '{"eligibility_result": "pass", "screen_failed": false}'
        mappings = [
            self._mapping(
                source_path="eligibility_result",
                fact_key="eligibility.passed",
                operator="equals",
                expected_value="pass",
            ),
            self._mapping(
                source_path="screen_failed",
                fact_key="screen_failed",
                operator="is_true",
                value_type="boolean",
            ),
        ]

        result = self.evaluator.build_facts(final_data=final_data, mappings=mappings)

        self.assertEqual(
            result,
            {
                "eligibility.passed": True,
                "screen_failed": False,
            },
        )

    def test_build_facts_supports_jsonpath_source_paths_from_page_state_final_data(self):
        final_data = {
            "page_state": {"status": "verified"},
            "fields": {
                "ELIGIBLE": {"value": True},
            },
            "query_summary": {
                "blocking_eligibility_query_count": 0,
            },
            "verification": {
                "required_eligibility_fields_verified": True,
            },
        }
        mappings = [
            self._mapping(
                source_path="$.page_state.status",
                fact_key="page_state.verified",
                operator="equals",
                expected_value="verified",
            ),
            self._mapping(
                source_path="$.fields.ELIGIBLE.value",
                fact_key="eligible",
                operator="is_true",
                value_type="boolean",
            ),
            self._mapping(
                source_path="$.query_summary.blocking_eligibility_query_count",
                fact_key="eligibility_queries.clear",
                operator="equals",
                expected_value="0",
                value_type="integer",
            ),
            self._mapping(
                source_path="$.verification.required_eligibility_fields_verified",
                fact_key="eligibility_fields.verified",
                operator="is_true",
                value_type="boolean",
            ),
        ]

        result = self.evaluator.build_facts(final_data=final_data, mappings=mappings)

        self.assertEqual(
            result,
            {
                "page_state.verified": True,
                "eligible": True,
                "eligibility_queries.clear": True,
                "eligibility_fields.verified": True,
            },
        )

    def test_build_facts_uses_jsonpath_parser_for_field_codes_containing_dots(self):
        final_data = {
            "fields": {
                "ELIGIBLE.CODE": {"value": "pass"},
            },
        }
        mappings = [
            self._mapping(
                source_path='$.fields["ELIGIBLE.CODE"].value',
                fact_key="eligible.code.pass",
                operator="equals",
                expected_value="pass",
            )
        ]

        result = self.evaluator.build_facts(final_data=json.dumps(final_data), mappings=mappings)

        self.assertEqual(result, {"eligible.code.pass": True})

    def test_build_facts_supports_multi_form_fact_source_entity(self):
        fact_source = DataCaptureFactSource(
            current_form_code="SCREENING_DEMOGRAPHICS",
            forms={
                "SCREENING_DEMOGRAPHICS": DataCaptureFactForm.from_raw(
                    data={
                        "format": "edc.form_data.v1",
                        "groups": {
                            "DEMOGRAPHICS": {
                                "kind": "single",
                                "items": {
                                    "AGE": "900",
                                    "DOB": "1212-01-02",
                                },
                            }
                        },
                    },
                    status="submitted",
                    open_queries=10,
                ),
                "SCREENING_INCLUSION_CRITERIA": DataCaptureFactForm.from_raw(
                    data={
                        "format": "edc.form_data.v1",
                        "groups": {
                            "INCLUSION": {
                                "kind": "single",
                                "items": {
                                    "ELIGIBLE": True,
                                },
                            }
                        },
                    },
                    status="verified",
                    open_queries=0,
                ),
            },
        )
        mappings = [
            self._mapping(
                source_path="$.SCREENING_DEMOGRAPHICS.status",
                fact_key="demographics.submitted",
                operator="equals",
                expected_value="submitted",
            ),
            self._mapping(
                source_path="$.SCREENING_DEMOGRAPHICS.open_queries",
                fact_key="demographics.has_open_queries",
                operator="gt",
                expected_value="0",
                value_type="integer",
            ),
            self._mapping(
                source_path="$.SCREENING_INCLUSION_CRITERIA.data.groups.INCLUSION.items.ELIGIBLE",
                fact_key="inclusion.eligible",
                operator="is_true",
                value_type="boolean",
            ),
            self._mapping(
                source_path="AGE",
                fact_key="current_form.age",
                operator="equals",
                expected_value="900",
            ),
        ]

        result = self.evaluator.build_facts(final_data=None, fact_source=fact_source, mappings=mappings)

        self.assertEqual(
            result,
            {
                "demographics.submitted": True,
                "demographics.has_open_queries": True,
                "inclusion.eligible": True,
                "current_form.age": True,
            },
        )

    def test_build_facts_returns_none_without_mapping_or_valid_final_data(self):
        self.assertIsNone(self.evaluator.build_facts(final_data='{"a": 1}', mappings=[]))
        self.assertIsNone(
            self.evaluator.build_facts(
                final_data="not-json",
                mappings=[
                    self._mapping(
                        source_path="a",
                        fact_key="a.ok",
                    )
                ],
            )
        )

    @staticmethod
    def _mapping(
        *,
        source_path,
        fact_key,
        operator="equals",
        expected_value=None,
        value_type="string",
    ):
        return DataCaptureFactMappingRule(
            id=1,
            source_path=source_path,
            fact_key=fact_key,
            operator=operator,
            expected_value=expected_value,
            value_type=value_type,
        )
