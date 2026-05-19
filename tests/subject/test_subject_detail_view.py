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

    def test_radio_display_value_uses_static_option_label(self):
        result = SubjectDetailView._display_value_for_control(
            raw_value="F",
            selected_values=["F"],
            options_config={
                "source": "static",
                "static": [
                    {"value": "M", "label": "Male"},
                    {"value": "F", "label": "Female"},
                ],
            },
            options=[
                {"value": "M", "label": "Male"},
                {"value": "F", "label": "Female"},
            ],
        )

        self.assertEqual(result, "Female")

    def test_checkbox_display_value_uses_static_option_labels(self):
        result = SubjectDetailView._display_value_for_control(
            raw_value="headache,nausea",
            selected_values=["headache", "nausea"],
            options_config={
                "source": "static",
                "static": [
                    {"value": "headache", "label": "Headache"},
                    {"value": "nausea", "label": "Nausea"},
                ],
            },
            options=[
                {"value": "headache", "label": "Headache"},
                {"value": "nausea", "label": "Nausea"},
            ],
        )

        self.assertEqual(result, "Headache, Nausea")

    def test_display_value_falls_back_to_raw_value_when_options_are_not_static(self):
        result = SubjectDetailView._display_value_for_control(
            raw_value="F",
            selected_values=["F"],
            options_config={
                "source": "lookup",
                "static": [{"value": "F", "label": "Female"}],
            },
            options=[{"value": "F", "label": "Female"}],
        )

        self.assertEqual(result, "F")


class SubjectDetailPageEntryFooterTests(SimpleTestCase):
    def _render_footer(self, **overrides):
        context = {
            "focused_event": {"id": 29, "is_repeating": False},
            "focused_form": {"id": 1},
            "event_file_import_url": "",
            "event_file_preview_url": "",
            "has_event_instance_files": False,
            "is_page_edit_locked": False,
            "is_viewing_submitted_version": False,
            "is_focused_render_draft_version": False,
            "datacapture_save_url": "/datacapture/save/",
            "can_show_datacapture_entry_actions": True,
        }
        context.update(overrides)
        return render_to_string("subject/includes/subject_detail_page_entry_footer.html", context)

    def test_event_file_import_stays_enabled_when_form_page_is_locked(self):
        rendered = self._render_footer(
            event_file_import_url="/studies/1/subjects/3/events/29/files/import/",
            is_page_edit_locked=True,
            can_show_datacapture_entry_actions=False,
        )

        self.assertIn("data-eventinstance-file-import-trigger", rendered)
        self.assertNotIn("data-eventinstance-file-import-trigger disabled", rendered)
        self.assertNotIn('aria-disabled="true"', rendered)

    def test_page_entry_actions_render_when_capture_actions_are_allowed(self):
        rendered = self._render_footer(can_show_datacapture_entry_actions=True)

        self.assertIn("data-datacapture-save", rendered)
        self.assertIn("data-datacapture-reset", rendered)
        self.assertIn("data-datacapture-submit", rendered)

    def test_page_entry_actions_are_hidden_when_capture_actions_are_blocked(self):
        rendered = self._render_footer(can_show_datacapture_entry_actions=False)

        self.assertNotIn("data-datacapture-save", rendered)
        self.assertNotIn("data-datacapture-reset", rendered)
        self.assertNotIn("data-datacapture-submit", rendered)
        self.assertNotIn(">Save<", rendered)
        self.assertNotIn(">Reset<", rendered)
        self.assertNotIn(">Submit for Review<", rendered)


class SubjectDetailPageEntryMainTests(SimpleTestCase):
    def test_page_entry_marks_field_with_open_query_and_renders_current_query_modal(self):
        rendered = render_to_string(
            "subject/includes/subject_detail_page_entry_main.html",
            {
                "LANGUAGE_CODE": "en",
                "focused_event": {"id": 1},
                "focused_form": {"id": 6, "title": "Vitals"},
                "focused_render_entry": {"id": 99},
                "focused_page_status": "submitted",
                "datacapture_save_url": "/api/save/",
                "datacapture_submit_url": "/api/submit/",
                "datacapture_delete_draft_url": "/api/delete-draft/",
                "datacapture_save_confirm_message": "",
                "datacapture_delete_draft_confirm_message": "",
                "is_viewing_submitted_version": False,
                "is_page_edit_locked": False,
                "page_entry_has_open_queries": True,
                "form_verification_query_thread_url": "/api/query-thread/",
                "form_render_sections": [
                    {
                        "layout_type": "grid",
                        "fields": [
                            {
                                "id": 11,
                                "field_key": "field_11",
                                "label": "Heart Rate",
                                "control_type": "text",
                                "value": "72",
                                "display_value": "72 bpm",
                                "active_query_id": 101,
                                "query_thread_badge_count": 2,
                                "query_messages": [
                                    {
                                        "dataquery_id": 101,
                                        "text": "Please confirm value",
                                        "status": "comment",
                                        "opened_by": "Reviewer",
                                        "opened_at": "05/18/2026 10:00",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        )

        self.assertIn("subject-form-field--has-open-query", rendered)
        self.assertIn("data-query-thread-modal-trigger", rendered)
        self.assertIn('data-active-query-id="101"', rendered)
        self.assertIn("images/datacapture/message.svg", rendered)
        self.assertIn("data-query-thread-badge", rendered)
        self.assertIn(">2</span>", rendered)
        self.assertIn('data-field-value="72 bpm"', rendered)
        self.assertIn("data-query-message-source", rendered)
        self.assertIn('data-message-text="Please confirm value"', rendered)
        self.assertIn("data-query-modal", rendered)
        self.assertIn('data-query-thread-url="/api/query-thread/"', rendered)
