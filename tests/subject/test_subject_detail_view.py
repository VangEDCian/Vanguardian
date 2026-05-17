from django.template.loader import render_to_string
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


class SubjectDetailPageEntryFooterTests(SimpleTestCase):
    def test_event_file_import_stays_enabled_when_form_page_is_locked(self):
        rendered = render_to_string(
            "subject/includes/subject_detail_page_entry_footer.html",
            {
                "focused_event": {"id": 29},
                "focused_form": {"id": 1},
                "event_file_import_url": "/studies/1/subjects/3/events/29/files/import/",
                "event_file_preview_url": "",
                "has_event_instance_files": False,
                "is_page_edit_locked": True,
                "is_viewing_submitted_version": False,
                "is_focused_render_draft_version": False,
                "datacapture_save_url": "/datacapture/save/",
            },
        )

        self.assertIn("data-eventinstance-file-import-trigger", rendered)
        self.assertNotIn("data-eventinstance-file-import-trigger disabled", rendered)
        self.assertNotIn('aria-disabled="true"', rendered)
