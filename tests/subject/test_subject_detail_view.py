from django.test import SimpleTestCase

from apps.subject.presentation.web.views import SubjectDetailView


class SubjectDetailViewChoiceOptionsTests(SimpleTestCase):
    def test_parse_choice_options_supports_json_value_label_list(self):
        raw_options = '[{"value":"M","label":"Male"},{"value":"F","label":"Female"}]'

        result = SubjectDetailView._parse_choice_options(raw_options)

        self.assertEqual(
            result,
            [
                {"value": "M", "label": "Male"},
                {"value": "F", "label": "Female"},
            ],
        )

    def test_parse_choice_options_keeps_legacy_key_value_format(self):
        raw_options = "Male=M Female=F"

        result = SubjectDetailView._parse_choice_options(raw_options)

        self.assertEqual(
            result,
            [
                {"label": "Male", "value": "M"},
                {"label": "Female", "value": "F"},
            ],
        )

