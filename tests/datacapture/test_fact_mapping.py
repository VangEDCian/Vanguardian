from django.test import SimpleTestCase

from apps.datacapture.domain import DataCaptureFactMappingEvaluator, DataCaptureFactMappingRule


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

    def test_build_facts_supports_nested_source_path(self):
        final_data = {
            "sections": {
                "screening": {
                    "fields": {
                        "age": {"value": "20"},
                    }
                }
            }
        }
        mappings = [
            self._mapping(
                source_path="sections.screening.fields.age.value",
                fact_key="age.ok",
                operator="gte",
                expected_value="18",
                value_type="integer",
            )
        ]

        result = self.evaluator.build_facts(final_data=final_data, mappings=mappings)

        self.assertEqual(result, {"age.ok": True})

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
