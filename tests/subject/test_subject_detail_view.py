from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.core.form_data_document import REPEAT_COUNTS_EXPORT_META_KEY
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

    def test_repeatable_section_renders_saved_repeat_instances(self):
        view = SubjectDetailView()

        sections = view._build_form_render_sections(
            [
                {
                    "id": "11",
                    "field_key": "AETERM",
                    "label": "AE Term",
                    "display_order": 1,
                    "section_template": {
                        "id": "7",
                        "code": "ADVERSE_EVENTS",
                        "name": "Adverse Events",
                        "display_order": 1,
                        "is_repeatable": True,
                        "max_repeats": 3,
                    },
                    "ui_config": {"control_type": "text"},
                }
            ],
            entry_payload_map={
                "AETERM": "Headache",
                "AETERM__repeat_2": "Nausea",
            },
        )

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["repeat_instance_index"], 1)
        self.assertEqual(sections[0]["fields"][0]["field_key"], "AETERM")
        self.assertFalse(sections[0]["can_add_repeat"])
        self.assertEqual(sections[1]["repeat_instance_index"], 2)
        self.assertEqual(sections[1]["fields"][0]["field_key"], "AETERM__repeat_2")
        self.assertEqual(sections[1]["fields"][0]["value"], "Nausea")
        self.assertTrue(sections[1]["can_add_repeat"])

    def test_repeatable_section_renders_blank_repeat_instance_from_payload_meta(self):
        view = SubjectDetailView()

        sections = view._build_form_render_sections(
            [
                {
                    "id": "11",
                    "field_key": "AETERM",
                    "label": "AE Term",
                    "display_order": 1,
                    "section_template": {
                        "id": "7",
                        "code": "ADVERSE_EVENTS",
                        "name": "Adverse Events",
                        "display_order": 1,
                        "is_repeatable": True,
                        "max_repeats": 3,
                    },
                    "ui_config": {"control_type": "text"},
                }
            ],
            entry_payload_map={
                REPEAT_COUNTS_EXPORT_META_KEY: {"ADVERSE_EVENTS": 2},
                "AETERM": "Headache",
            },
        )

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[1]["repeat_instance_index"], 2)
        self.assertEqual(sections[1]["fields"][0]["field_key"], "AETERM__repeat_2")
        self.assertEqual(sections[1]["fields"][0]["display_value"], "")

    def test_extract_entry_payload_map_flattens_canonical_date_values(self):
        payload = SubjectDetailView._extract_entry_payload_map(
            """
            {
                "format": "edc.form_data.v1",
                "groups": {
                    "DEMOGRAPHICS": {
                        "kind": "single",
                        "items": {
                            "AGE": "66",
                            "DOB": "1960-05-25",
                            "ICF_DATE": "2026-05-25",
                            "SEX": "M"
                        }
                    }
                }
            }
            """
        )

        self.assertEqual(payload["DOB"], "1960-05-25")
        self.assertEqual(payload["ICF_DATE"], "2026-05-25")

    def test_repeat_table_section_groups_repeat_instances_as_rows(self):
        view = SubjectDetailView()

        sections = view._build_form_render_sections(
            [
                {
                    "id": "11",
                    "field_key": "MED_NAME",
                    "label": "Medication",
                    "display_order": 1,
                    "section_template": {
                        "id": "7",
                        "code": "MEDICATION_HISTORY",
                        "name": "Medication History",
                        "display_order": 1,
                        "is_repeatable": True,
                        "max_repeats": 3,
                        "layout_config": {
                            "layout_type": "repeat_table",
                            "custom_layout_schema": {"show_row_number": True},
                        },
                    },
                    "ui_config": {"control_type": "text"},
                },
                {
                    "id": "12",
                    "field_key": "MED_REASON",
                    "label": "Reason",
                    "display_order": 2,
                    "section_template": {
                        "id": "7",
                        "code": "MEDICATION_HISTORY",
                        "name": "Medication History",
                        "display_order": 1,
                        "is_repeatable": True,
                        "max_repeats": 3,
                        "layout_config": {
                            "layout_type": "repeat_table",
                            "custom_layout_schema": {"show_row_number": True},
                        },
                    },
                    "ui_config": {"control_type": "text"},
                },
            ],
            entry_payload_map={
                "MED_NAME": "Paracetamol",
                "MED_REASON": "Pain",
                "MED_NAME__repeat_2": "Aspirin",
                "MED_REASON__repeat_2": "Fever",
            },
        )

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["layout_type"], "repeat_table")
        self.assertTrue(sections[0]["can_add_repeat"])
        self.assertEqual(len(sections[0]["repeat_table_rows"]), 2)
        self.assertEqual(sections[0]["repeat_table_rows"][0]["fields"][0]["field_key"], "MED_NAME")
        self.assertEqual(
            sections[0]["repeat_table_rows"][1]["fields"][0]["field_key"],
            "MED_NAME__repeat_2",
        )
        self.assertEqual(sections[0]["repeat_table_rows"][1]["fields"][1]["value"], "Fever")

    def test_date_text_and_datetime_text_control_types_are_supported(self):
        view = SubjectDetailView()

        self.assertEqual(view._normalize_control_type("DATE_TEXT"), "date_text")
        self.assertEqual(view._normalize_control_type("DATETIME_TEXT"), "datetime_text")
        self.assertEqual(view._normalize_control_type("TIME"), "time")
        self.assertEqual(view._normalize_control_type("time_picker"), "time")

    def test_field_render_resolves_time_control_template(self):
        rendered = render_to_string(
            "subject/components/_field_render.html",
            {
                "field": {
                    "id": 12,
                    "field_key": "VISIT_TIME",
                    "label": "Visit Time",
                    "control_type": "TIME",
                    "value": "08:30:00",
                    "is_required": True,
                },
            },
        )

        self.assertIn('class="subject-date-text"', rendered)
        self.assertIn("subject-date-text__input", rendered)
        self.assertIn('type="time"', rendered)
        self.assertIn('name="VISIT_TIME"', rendered)
        self.assertIn("data-dateandtime-input", rendered)
        self.assertIn("data-dateandtime-time", rendered)
        self.assertIn('data-dateandtime-kind="time"', rendered)
        self.assertIn('data-submitted-diff-control="time"', rendered)
        self.assertIn("data-standalone-time-input", rendered)
        self.assertIn('value="08:30"', rendered)
        self.assertNotIn("\n       readonly", rendered)

    def test_time_control_does_not_render_invalid_html_time_value(self):
        rendered = render_to_string(
            "subject/components/_field_render.html",
            {
                "field": {
                    "id": 12,
                    "field_key": "VISIT_TIME",
                    "label": "Visit Time",
                    "control_type": "TIME",
                    "value": "3232-",
                    "is_required": False,
                },
            },
        )

        self.assertIn('type="time"', rendered)
        self.assertIn('value=""', rendered)

    def test_number_control_renders_range_and_precision_attrs(self):
        rendered = render_to_string(
            "subject/components/_field_render.html",
            {
                "field": {
                    "id": 13,
                    "field_key": "WEIGHT",
                    "label": "Weight",
                    "control_type": "NUMBER",
                    "range_min": "-10.5",
                    "range_max": "120.25",
                    "precision": 2,
                    "value": "72.345",
                    "is_required": True,
                },
            },
        )

        self.assertIn('data-validator-type="number"', rendered)
        self.assertIn('data-range-min="-10.5"', rendered)
        self.assertIn('data-range-max="120.25"', rendered)
        self.assertIn('data-precision="2"', rendered)
        self.assertIn('inputmode="decimal"', rendered)


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
            "workflow_action_trigger_url": "",
            "request": SimpleNamespace(get_full_path="/studies/1/subjects/20/?event=29"),
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

    def test_trigger_workflow_action_is_not_rendered_in_detail_footer(self):
        rendered = self._render_footer(
            workflow_action_trigger_url="/studies/1/subjects/20/events/60/trigger-workflow/",
            can_show_datacapture_entry_actions=False,
        )

        self.assertNotIn("Trigger Workflow", rendered)
        self.assertNotIn("/studies/1/subjects/20/events/60/trigger-workflow/", rendered)


class SubjectDetailPageEntryMainTests(SimpleTestCase):
    def test_radio_control_renders_clear_button_after_options(self):
        rendered = render_to_string(
            "subject/components/controls/_radio_control.html",
            {
                "choice_list_class": "subject-form-field-card__choice-list",
                "field": {
                    "field_key": "SEX",
                    "value": "F",
                    "options": [
                        {"value": "M", "label": "Male"},
                        {"value": "F", "label": "Female"},
                    ],
                },
                "is_page_edit_locked": False,
            },
        )

        self.assertIn('data-radio-clear', rendered)
        self.assertIn('type="button"', rendered)
        self.assertIn("Clear", rendered)
        self.assertLess(rendered.index("Female"), rendered.index("data-radio-clear"))
        self.assertNotIn('data-radio-clear disabled', rendered)

    def test_radio_control_clear_button_is_disabled_when_page_is_locked(self):
        rendered = render_to_string(
            "subject/components/controls/_radio_control.html",
            {
                "choice_list_class": "subject-form-field-card__choice-list",
                "field": {
                    "field_key": "SEX",
                    "value": "F",
                    "options": [
                        {"value": "M", "label": "Male"},
                        {"value": "F", "label": "Female"},
                    ],
                },
                "is_page_edit_locked": True,
            },
        )

        self.assertIn("data-radio-clear", rendered)
        self.assertIn("disabled", rendered)
        self.assertIn('aria-disabled="true"', rendered)

    def test_date_text_control_renders_locale_mask_and_hidden_value(self):
        rendered = render_to_string(
            "subject/components/controls/_date_text_control.html",
            {
                "LANGUAGE_CODE": "vi",
                "field": {
                    "field_key": "VISIT_DATE",
                    "label": "Visit Date",
                    "value": "2026-02-12",
                    "date_day": "12",
                    "date_month": "2",
                    "date_year": "2026",
                    "is_required": True,
                },
            },
        )

        self.assertIn("data-date-text-composite-input", rendered)
        self.assertIn('data-date-text-kind="date"', rendered)
        self.assertIn('data-date-text-locale="vi"', rendered)
        self.assertIn('placeholder="dd/MM/yyyy"', rendered)
        self.assertIn('value="2026-02-12"', rendered)

    def test_datetime_text_control_renders_en_locale_mask(self):
        rendered = render_to_string(
            "subject/components/controls/_datetime_text_control.html",
            {
                "LANGUAGE_CODE": "en",
                "field": {
                    "field_key": "VISIT_AT",
                    "label": "Visit At",
                    "value": "2026-12-02 09:30:00",
                    "date_day": "2",
                    "date_month": "12",
                    "date_year": "2026",
                    "date_time": "09:30",
                    "is_required": False,
                },
            },
        )

        self.assertIn("data-date-text-composite-input", rendered)
        self.assertIn('data-date-text-kind="datetime"', rendered)
        self.assertIn('data-date-text-locale="en"', rendered)
        self.assertIn('placeholder="MM/dd/yyyy HH:mm"', rendered)
        self.assertIn('value="2026-12-02 09:30:00"', rendered)

    def test_field_render_resolves_date_text_control_template(self):
        rendered = render_to_string(
            "subject/components/_field_render.html",
            {
                "LANGUAGE_CODE": "vi",
                "field": {
                    "id": 11,
                    "field_key": "VISIT_DATE",
                    "label": "Visit Date",
                    "control_type": "date_text",
                    "value": "2026-02-12",
                    "date_day": "12",
                    "date_month": "2",
                    "date_year": "2026",
                },
            },
        )

        self.assertIn("data-date-text-input", rendered)
        self.assertIn('data-date-text-kind="date"', rendered)

    def test_date_picker_control_uses_native_date_input(self):
        rendered = render_to_string(
            "subject/components/controls/_date_picker_control.html",
            {
                "LANGUAGE_CODE": "vi",
                "field": {
                    "field_key": "VISIT_DATE",
                    "label": "Visit Date",
                    "value": "2026-02-12",
                    "date_day": "12",
                    "date_month": "2",
                    "date_year": "2026",
                },
            },
        )

        self.assertIn("data-dateandtime-input", rendered)
        self.assertIn("data-dateandtime-control", rendered)
        self.assertIn("data-dateandtime-date", rendered)
        self.assertIn('data-dateandtime-kind="date"', rendered)
        self.assertIn('data-dateandtime-locale="vi"', rendered)
        self.assertIn('type="date"', rendered)
        self.assertIn('lang="vi"', rendered)
        self.assertIn('value="2026-02-12"', rendered)
        self.assertNotIn("subject-date-picker__part", rendered)

    def test_datetime_control_uses_native_date_and_time_inputs(self):
        rendered = render_to_string(
            "subject/components/controls/_datetime_control.html",
            {
                "LANGUAGE_CODE": "en",
                "field": {
                    "field_key": "VISIT_AT",
                    "label": "Visit At",
                    "value": "2026-12-02 09:30:00",
                    "date_day": "2",
                    "date_month": "12",
                    "date_year": "2026",
                    "date_time": "09:30",
                },
            },
        )

        self.assertIn("data-dateandtime-input", rendered)
        self.assertIn("data-dateandtime-control", rendered)
        self.assertIn("data-dateandtime-date", rendered)
        self.assertIn("data-dateandtime-time", rendered)
        self.assertIn('data-dateandtime-kind="datetime"', rendered)
        self.assertIn('data-dateandtime-locale="en"', rendered)
        self.assertIn('type="date"', rendered)
        self.assertIn('type="time"', rendered)
        self.assertIn('lang="en"', rendered)
        self.assertIn('value="2026-12-02"', rendered)
        self.assertIn('value="09:30"', rendered)
        self.assertNotIn("subject-date-picker__part", rendered)

    def test_repeat_table_section_renders_headers_rows_and_add_button(self):
        rendered = render_to_string(
            "subject/components/_section_render.html",
            {
                "hide_section_title": False,
                "can_add_repeat_sections": True,
                "section": {
                    "id": "7",
                    "title": "Medication History",
                    "layout_type": "repeat_table",
                    "show_section_header": True,
                    "repeat_instance_index": 1,
                    "current_repeats": 1,
                    "max_repeats": 3,
                    "can_add_repeat": True,
                    "repeat_table_layout": {
                        "show_table_header": True,
                        "show_row_number": True,
                        "row_number_label": "STT",
                        "row_number_width": "56px",
                    },
                    "fields": [
                        {
                            "id": 11,
                            "field_key": "MED_NAME",
                            "label": "Medication",
                            "control_type": "text",
                            "is_required": False,
                        }
                    ],
                    "repeat_table_rows": [
                        {
                            "repeat_instance_index": 1,
                            "fields": [
                                {
                                    "id": 11,
                                    "field_key": "MED_NAME",
                                    "label": "Medication",
                                    "control_type": "text",
                                    "value": "",
                                }
                            ],
                        }
                    ],
                },
            },
        )

        self.assertIn("Medication History", rendered)
        self.assertIn("Medication", rendered)
        self.assertIn("data-repeat-table-body", rendered)
        self.assertIn("data-repeat-table-row", rendered)
        self.assertIn("data-repeat-table-row-delete", rendered)
        self.assertIn("images/datacapture/delete.svg", rendered)
        self.assertIn("data-repeat-section-add", rendered)

    def test_repeatable_section_add_button_renders_when_below_max_repeats(self):
        rendered = render_to_string(
            "subject/includes/subject_detail_page_entry_main.html",
            {
                "focused_event": {"id": 1},
                "focused_form": {"id": 6, "title": "Adverse Events"},
                "focused_render_entry": {"id": 99},
                "focused_page_status": "in_progress",
                "datacapture_save_url": "/api/save/",
                "datacapture_submit_url": "/api/submit/",
                "is_viewing_submitted_version": False,
                "is_page_edit_locked": False,
                "form_render_sections": [
                    {
                        "id": "7",
                        "title": "Adverse Events",
                        "layout_type": "grid",
                        "repeat_instance_index": 1,
                        "current_repeats": 1,
                        "max_repeats": 3,
                        "is_repeatable": True,
                        "can_add_repeat": True,
                        "fields": [
                            {
                                "id": 11,
                                "field_key": "AETERM",
                                "label": "AE Term",
                                "control_type": "text",
                                "value": "",
                            },
                        ],
                    }
                ],
            },
        )

        self.assertIn("data-repeat-section-add", rendered)
        self.assertIn("data-repeat-section-delete", rendered)
        self.assertIn("Delete Item", rendered)
        self.assertIn("Thêm Adverse Events", rendered)
        self.assertIn('data-section-template-id="7"', rendered)
        self.assertIn('data-max-repeats="3"', rendered)

    def test_section_render_sorts_fields_by_display_order(self):
        rendered = render_to_string(
            "subject/components/_section_render.html",
            {
                "hide_section_title": False,
                "section": {
                    "id": "7",
                    "title": "Vitals",
                    "layout_type": "grid",
                    "show_section_header": True,
                    "fields": [
                        {
                            "id": 12,
                            "field_key": "SECOND",
                            "label": "Second",
                            "display_order": 2,
                            "control_type": "text",
                        },
                        {
                            "id": 11,
                            "field_key": "FIRST",
                            "label": "First",
                            "display_order": 1,
                            "control_type": "text",
                        },
                    ],
                },
            },
        )

        self.assertLess(rendered.index('data-field-key="FIRST"'), rendered.index('data-field-key="SECOND"'))

    def test_table_section_render_sorts_fields_by_display_order(self):
        rendered = render_to_string(
            "subject/components/_section_table_render.html",
            {
                "hide_section_title": False,
                "section": {
                    "id": "7",
                    "title": "Eligibility",
                    "show_section_header": True,
                    "table_layout": {
                        "response_direction": "horizontal",
                        "show_table_header": False,
                        "columns": [{"label": "Question"}, {"label": "Response"}],
                    },
                    "fields": [
                        {
                            "id": 12,
                            "field_key": "SECOND",
                            "label": "Second",
                            "display_order": 2,
                            "control_type": "text",
                            "table_row_cells": [{"kind": "text", "text": "Second"}],
                        },
                        {
                            "id": 11,
                            "field_key": "FIRST",
                            "label": "First",
                            "display_order": 1,
                            "control_type": "text",
                            "table_row_cells": [{"kind": "text", "text": "First"}],
                        },
                    ],
                },
            },
        )

        self.assertLess(rendered.index('data-field-key="FIRST"'), rendered.index('data-field-key="SECOND"'))

    def test_repeat_table_render_sorts_headers_and_row_fields_by_display_order(self):
        rendered = render_to_string(
            "subject/components/_section_repeat_table_render.html",
            {
                "can_add_repeat_sections": False,
                "hide_section_title": False,
                "section": {
                    "id": "7",
                    "title": "Medication History",
                    "show_section_header": True,
                    "repeat_table_layout": {
                        "show_table_header": True,
                        "show_row_number": False,
                    },
                    "fields": [
                        {
                            "id": 12,
                            "field_key": "SECOND",
                            "label": "Second",
                            "display_order": 2,
                            "control_type": "text",
                        },
                        {
                            "id": 11,
                            "field_key": "FIRST",
                            "label": "First",
                            "display_order": 1,
                            "control_type": "text",
                        },
                    ],
                    "repeat_table_rows": [
                        {
                            "repeat_instance_index": 1,
                            "fields": [
                                {
                                    "id": 12,
                                    "field_key": "SECOND",
                                    "label": "Second",
                                    "display_order": 2,
                                    "control_type": "text",
                                },
                                {
                                    "id": 11,
                                    "field_key": "FIRST",
                                    "label": "First",
                                    "display_order": 1,
                                    "control_type": "text",
                                },
                            ],
                        }
                    ],
                },
            },
        )

        self.assertLess(rendered.index("First"), rendered.index("Second"))
        self.assertLess(rendered.index('data-field-key="FIRST"'), rendered.index('data-field-key="SECOND"'))

    def test_subject_detail_loads_sidebar_scroll_script_for_page_entry_form(self):
        rendered = render_to_string(
            "subject/subject_detail.html",
            {
                "focused_forms": [{"id": 6, "title": "Vitals", "focus_url": "/subjects/1/?event=1&form=6"}],
                "event_navigation": [
                    {
                        "id": 1,
                        "name": "Visit 1",
                        "status": "open",
                        "focus_url": "/subjects/1/?event=1",
                        "is_repeating": False,
                        "forms": [
                            {
                                "id": 6,
                                "title": "Vitals",
                                "focus_url": "/subjects/1/?event=1&form=6",
                            }
                        ],
                    }
                ],
                "focused_event": {"id": 1},
                "focused_form": {"id": 6, "title": "Vitals"},
                "focused_render_entry": {"id": 99},
                "focused_page_status": "in_progress",
                "datacapture_save_url": "/api/save/",
                "datacapture_submit_url": "/api/submit/",
                "is_form_verification_mode": False,
                "is_subject_detail_viewonly_mode": False,
                "is_viewing_submitted_version": False,
                "is_page_edit_locked": False,
                "form_render_sections": [],
                "current_data_values": {},
                "previous_data_values": None,
                "previous_submitted_entry_values": {},
                "reason_required_field_keys": [],
                "page_entry_has_open_queries": False,
                "subject_display_id": "SUBJ-001",
                "subject_obj": {"site": {"code": "SITE-01"}, "screening_code": "SCR-01"},
                "study_header_label": "Study A",
                "back_url": "/subjects/",
                "auth_user": {"is_superuser": False, "display_name": "Demo User", "username": "demo", "email": ""},
                "shared_study_selected_id": 1,
                "shared_study_select_default": "Study A",
                "shared_study_select_options": [],
                "shared_study_cookies_key": "study",
                "shared_site_select_default": "Site 01",
                "shared_site_select_options": [],
                "shared_site_cookies_key": "site",
                "shared_language_select_options": [],
                "layout_nav_key": "",
                "layout_show_breadcrumb_trail": False,
                "layout_detail_meta_items": [],
            },
        )

        self.assertIn("subject/js/subject_detail_sidebar_scroll.js", rendered)
        self.assertIn('class="subject-detail-sidebar__child is-active"', rendered)

    def test_subject_detail_marks_repeating_event_group_active_for_sidebar_scroll(self):
        rendered = render_to_string(
            "subject/subject_detail.html",
            {
                "focused_forms": [{"id": 6, "title": "Vitals", "focus_url": "/subjects/1/?event=2&form=6"}],
                "event_navigation": [
                    {
                        "id": "2",
                        "event_definition_id": "20",
                        "name": "Unscheduled Visit",
                        "status": "open",
                        "focus_url": "/subjects/1/?event=2",
                        "is_repeating": True,
                        "forms": [
                            {
                                "id": 6,
                                "title": "Vitals",
                                "focus_url": "/subjects/1/?event=2&form=6",
                            }
                        ],
                        "repeat_event_instances": [],
                    }
                ],
                "focused_event": {"id": "2", "event_definition_id": "20"},
                "focused_form": {"id": 6, "title": "Vitals"},
                "focused_render_entry": {"id": 99},
                "focused_page_status": "in_progress",
                "datacapture_save_url": "/api/save/",
                "datacapture_submit_url": "/api/submit/",
                "is_form_verification_mode": False,
                "is_subject_detail_viewonly_mode": False,
                "is_viewing_submitted_version": False,
                "is_page_edit_locked": False,
                "form_render_sections": [],
                "current_data_values": {},
                "previous_data_values": None,
                "previous_submitted_entry_values": {},
                "reason_required_field_keys": [],
                "page_entry_has_open_queries": False,
                "subject_display_id": "SUBJ-001",
                "subject_obj": {"site": {"code": "SITE-01"}, "screening_code": "SCR-01"},
                "study_header_label": "Study A",
                "back_url": "/subjects/",
                "auth_user": {"is_superuser": False, "display_name": "Demo User", "username": "demo", "email": ""},
                "shared_study_selected_id": 1,
                "shared_study_select_default": "Study A",
                "shared_study_select_options": [],
                "shared_study_cookies_key": "study",
                "shared_site_select_default": "Site 01",
                "shared_site_select_options": [],
                "shared_site_cookies_key": "site",
                "shared_language_select_options": [],
                "layout_nav_key": "",
                "layout_show_breadcrumb_trail": False,
                "layout_detail_meta_items": [],
            },
        )

        self.assertIn("subject/js/subject_detail_sidebar_scroll.js", rendered)
        self.assertIn('class="subject-detail-sidebar__group is-active"', rendered)

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
        self.assertIn('data-query-can-respond="true"', rendered)
        self.assertIn(">2</span>", rendered)
        self.assertIn('data-field-value="72 bpm"', rendered)
        self.assertIn("data-query-message-source", rendered)
        self.assertIn('data-message-text="Please confirm value"', rendered)
        self.assertIn("data-query-modal", rendered)
        self.assertIn('data-query-thread-url="/api/query-thread/"', rendered)
