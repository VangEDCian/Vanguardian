from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class FormVerificationTemplateTests(SimpleTestCase):
    def _render_field_review_table(
        self,
        *,
        show_checkboxes: bool,
        fields_locked: bool = False,
        show_actions: bool = True,
        active_query_id: int | None = 101,
        query_thread_badge_count: int = 2,
        is_checked: bool = False,
        has_verified_query: bool = False,
        open_query_count: int = 0,
        closed_query_histories: list[dict] | None = None,
        active_query_is_answered: bool = False,
        active_query_can_respond: bool = True,
        query_actions_locked: bool = False,
        show_actions_column: bool = True,
    ) -> str:
        return render_to_string(
            "subject/includes/form_verification_field_review_table.html",
            {
                "LANGUAGE_CODE": "en",
                "form_verification_fields_locked": fields_locked,
                "form_verification_query_actions_locked": query_actions_locked,
                "form_verification_show_actions_column": show_actions_column,
                "form_verification_show_field_checkboxes": show_checkboxes,
                "form_verification_show_actions": show_actions,
                "form_verification_review": SimpleNamespace(
                    rows=[
                        {
                            "field_template_id": 11,
                            "field_key": "field_11",
                            "is_checked": is_checked,
                            "brief_description": "Field 1",
                            "display_value": "Value 1",
                            "open_query_count": open_query_count,
                            "active_query_id": active_query_id,
                            "active_query_is_answered": active_query_is_answered,
                            "active_query_can_respond": active_query_can_respond,
                            "has_verified_query": has_verified_query,
                            "closed_query_histories": closed_query_histories or [],
                            "query_thread_badge_count": query_thread_badge_count,
                            "query_messages": [
                                {
                                    "dataquery_id": 101,
                                    "text": "Newest query",
                                    "status": "open",
                                    "opened_by": "Reviewer",
                                    "opened_at": "05/18/2026 10:00",
                                },
                            ],
                            "modified_by": "User 1",
                        }
                    ],
                ),
            },
        )

    def test_field_review_table_disables_checkboxes_when_status_is_not_reviewable_ui_state(self):
        rendered = self._render_field_review_table(show_checkboxes=False)

        self.assertIn('name="verify_field"', rendered)
        self.assertIn("subject-form-verification-review__col-check", rendered)
        self.assertIn("disabled", rendered)
        self.assertIn('aria-disabled="true"', rendered)

    def test_field_review_table_hides_actions_column_without_submitted_entry(self):
        rendered = self._render_field_review_table(
            show_checkboxes=False,
            show_actions=False,
            active_query_id=None,
            query_thread_badge_count=0,
            show_actions_column=False,
        )

        self.assertNotIn(">Actions<", rendered)
        self.assertNotIn("data-query-modal-trigger", rendered)
        self.assertNotIn("data-query-thread-modal-trigger", rendered)

    def test_field_review_action_button_is_enabled_when_page_status_is_not_locked(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=None,
            query_thread_badge_count=0,
        )

        action_button = self._action_button_markup(rendered, "data-query-modal-trigger")

        self.assertIn("subject-form-verification-review__action-btn", action_button)
        self.assertNotIn("hidden", action_button)
        self.assertNotIn("disabled", action_button)
        self.assertNotIn('aria-disabled="true"', action_button)
        self.assertIn("data-query-modal-trigger", action_button)
        self.assertIn('data-field-template-id="11"', action_button)
        self.assertIn('data-field-label="Field 1"', action_button)
        self.assertIn('data-field-key="field_11"', action_button)
        self.assertIn('data-field-value="Value 1"', action_button)

    def test_field_review_action_button_is_hidden_when_field_has_open_query(self):
        rendered = self._render_field_review_table(show_checkboxes=True, fields_locked=False)

        action_button = self._action_button_markup(rendered, "data-query-modal-trigger")

        self.assertIn("hidden", action_button)

    def test_field_review_action_button_is_hidden_when_field_is_verified(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=None,
            query_thread_badge_count=0,
            is_checked=True,
        )

        action_button = self._action_button_markup(rendered, "data-query-modal-trigger")

        self.assertIn("hidden", action_button)

    def test_field_review_table_hides_verified_rows_by_default_filter(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=None,
            query_thread_badge_count=0,
            is_checked=True,
        )

        row_start = rendered.index('data-field-template-id="11"')
        tr_start = rendered.rfind("<tr", 0, row_start)
        tr_end = rendered.index(">", row_start)
        row = rendered[tr_start : tr_end + 1]

        self.assertIn('data-field-verified="true"', row)
        self.assertIn("hidden", row)

    def test_field_review_checkbox_stays_enabled_when_verified_field_is_reviewable(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=None,
            query_thread_badge_count=0,
            is_checked=True,
        )

        checkbox_start = rendered.index('name="verify_field"')
        input_start = rendered.rfind("<input", 0, checkbox_start)
        input_end = rendered.index(">", checkbox_start)
        checkbox = rendered[input_start : input_end + 1]

        self.assertIn("checked", checkbox)
        self.assertNotIn("disabled", checkbox)
        self.assertNotIn('aria-disabled="true"', checkbox)

    def test_field_review_action_button_is_hidden_when_field_has_verified_query(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=None,
            query_thread_badge_count=0,
            has_verified_query=True,
        )

        action_button = self._action_button_markup(rendered, "data-query-modal-trigger")

        self.assertIn("hidden", action_button)

    def test_field_review_checkbox_is_disabled_when_field_has_open_query(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            active_query_id=101,
            open_query_count=1,
        )

        checkbox_start = rendered.index('name="verify_field"')
        input_start = rendered.rfind("<input", 0, checkbox_start)
        input_end = rendered.index(">", checkbox_start)
        checkbox = rendered[input_start : input_end + 1]

        self.assertIn("disabled", checkbox)
        self.assertIn('aria-disabled="true"', checkbox)
        self.assertIn('data-blocked-by-open-query="true"', checkbox)

    def test_field_review_action_button_is_disabled_when_page_status_is_locked(self):
        rendered = self._render_field_review_table(show_checkboxes=True, fields_locked=True)

        action_button = self._action_button_markup(rendered, "data-query-modal-trigger")

        self.assertIn("subject-form-verification-review__action-btn", action_button)
        self.assertIn("disabled", action_button)
        self.assertIn('aria-disabled="true"', action_button)

    def test_field_review_open_query_is_disabled_but_current_query_stays_clickable_when_query_actions_are_locked(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            fields_locked=False,
            query_actions_locked=True,
            active_query_id=101,
            query_thread_badge_count=1,
        )

        open_query_button = self._action_button_markup(rendered, "data-query-modal-trigger")
        current_query_button = self._action_button_markup(rendered, "data-query-thread-modal-trigger")

        self.assertIn("subject-form-verification-review__action-btn", open_query_button)
        self.assertIn("disabled", open_query_button)
        self.assertIn('aria-disabled="true"', open_query_button)
        self.assertNotIn("disabled", current_query_button)
        self.assertNotIn('aria-disabled="true"', current_query_button)
        self.assertIn('data-query-can-respond="true"', current_query_button)

    def test_field_review_current_query_embeds_readonly_permission_flag(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            active_query_id=101,
            active_query_can_respond=False,
        )

        current_query_button = self._action_button_markup(rendered, "data-query-thread-modal-trigger")

        self.assertNotIn("disabled", current_query_button)
        self.assertIn('data-query-can-respond="false"', current_query_button)

    def test_field_review_table_embeds_latest_query_messages_for_modal(self):
        rendered = self._render_field_review_table(show_checkboxes=True)

        self.assertIn("data-query-message-source", rendered)
        self.assertIn('data-message-dataquery-id="101"', rendered)
        self.assertIn('data-message-text="Newest query"', rendered)
        self.assertIn('data-message-status="open"', rendered)
        self.assertIn('data-message-opened-by="Reviewer"', rendered)

    def test_field_review_table_renders_queries_button_with_badge(self):
        rendered = self._render_field_review_table(show_checkboxes=True)

        queries_button = self._action_button_markup(rendered, "data-query-thread-modal-trigger")

        self.assertIn("data-query-thread-modal-trigger", queries_button)
        self.assertIn('data-active-query-id="101"', queries_button)
        self.assertIn('data-field-template-id="11"', queries_button)
        self.assertIn('title="Current Query"', queries_button)
        self.assertIn('aria-label="Current Query"', queries_button)
        self.assertNotIn("hidden", queries_button)
        self.assertIn("images/datacapture/message.svg", rendered)
        self.assertIn("data-query-thread-badge", rendered)
        self.assertIn(">2</span>", rendered)

    def test_field_review_table_hides_current_query_button_without_open_query(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            active_query_id=None,
            query_thread_badge_count=0,
        )

        queries_button = self._action_button_markup(rendered, "data-query-thread-modal-trigger")

        self.assertIn("hidden", queries_button)
        self.assertIn("disabled", queries_button)
        self.assertIn('aria-disabled="true"', queries_button)
        self.assertNotIn("data-query-thread-badge", rendered)

    def test_field_review_table_marks_current_query_button_when_query_is_answered(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            active_query_id=101,
            active_query_is_answered=True,
        )

        queries_button = self._action_button_markup(rendered, "data-query-thread-modal-trigger")

        self.assertIn('data-query-answered="true"', queries_button)

    def test_field_review_table_shows_queries_history_button_for_closed_queries(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            active_query_id=None,
            query_thread_badge_count=0,
            closed_query_histories=[
                {
                    "dataquery_id": 201,
                    "label": "Query #201",
                    "opened_at": "05/18/2026 09:00",
                    "closed_at": "05/18/2026 10:00",
                    "messages": [
                        {
                            "dataquery_id": 201,
                            "text": "Closed message",
                            "status": "comment",
                            "opened_by": "Reviewer",
                            "opened_at": "05/18/2026 09:30",
                        },
                    ],
                },
            ],
        )

        history_button = self._action_button_markup(rendered, "data-query-history-modal-trigger")

        self.assertIn('title="Queries History"', history_button)
        self.assertIn("images/datacapture/history.svg", rendered)
        self.assertNotIn("hidden", history_button)
        self.assertIn("data-query-history-source", rendered)
        self.assertIn('data-history-dataquery-id="201"', rendered)
        self.assertIn('data-message-text="Closed message"', rendered)

    def test_field_review_table_hides_queries_history_button_without_closed_queries(self):
        rendered = self._render_field_review_table(
            show_checkboxes=True,
            active_query_id=None,
            query_thread_badge_count=0,
        )

        history_button = self._action_button_markup(rendered, "data-query-history-modal-trigger")

        self.assertIn("hidden", history_button)

    def test_field_review_table_renders_repeat_group_item_context(self):
        rendered = render_to_string(
            "subject/includes/form_verification_field_review_table.html",
            {
                "LANGUAGE_CODE": "en",
                "form_verification_fields_locked": False,
                "form_verification_query_actions_locked": False,
                "form_verification_show_actions_column": True,
                "form_verification_show_field_checkboxes": True,
                "form_verification_review": SimpleNamespace(
                    rows=[
                        {
                            "field_template_id": 21,
                            "field_key": "MED_NAME__repeat_2",
                            "repeat_instance_index": 2,
                            "is_repeatable_group_item": True,
                            "section_code": "MEDS",
                            "section_title": "Medication History",
                            "group_item_label": "2",
                            "is_checked": False,
                            "brief_description": "Medication",
                            "display_value": "Paracetamol",
                            "open_query_count": 0,
                            "active_query_id": None,
                            "active_query_is_answered": False,
                            "active_query_can_respond": False,
                            "has_verified_query": False,
                            "closed_query_histories": [],
                            "query_thread_badge_count": 0,
                            "query_messages": [],
                            "modified_by": "User 1",
                        }
                    ],
                ),
            },
        )

        self.assertIn('data-field-key="MED_NAME__repeat_2"', rendered)
        self.assertIn('data-repeat-instance-index="2"', rendered)
        self.assertIn('data-section-code="MEDS"', rendered)
        self.assertIn("Medication History", rendered)
        self.assertIn("Group Item", rendered)

    def test_field_review_panel_renders_open_query_and_thread_query_modals(self):
        rendered = render_to_string(
            "subject/includes/form_verification_field_review.html",
            {
                "LANGUAGE_CODE": "vi",
                "form_verification_fields_locked": False,
                "form_verification_query_actions_locked": False,
                "form_verification_show_actions_column": True,
                "form_verification_show_field_checkboxes": True,
                "form_verification_show_actions": True,
                "form_verification_open_query_url": "/open-query/",
                "form_verification_query_thread_url": "/query-thread/",
                "focused_render_entry": SimpleNamespace(id=101),
                "form_verification_review": SimpleNamespace(
                    header={
                        "event_name": "Visit 1",
                        "event_start_date": "05/18/2026",
                        "form_name": "Vitals",
                        "form_status": "submitted",
                        "form_version": "1",
                        "last_modified": "05/18/2026",
                    },
                    rows=[],
                ),
            },
        )

        self.assertIn('data-review-page-entry-id="101"', rendered)
        self.assertIn('data-review-entry-version="1"', rendered)
        self.assertIn('data-review-page-status="submitted"', rendered)
        self.assertIn("data-open-query-modal", rendered)
        self.assertIn('data-open-query-url="/open-query/"', rendered)
        self.assertIn("data-open-query-modal-comment-input", rendered)
        self.assertIn("data-open-query-modal-submit", rendered)
        self.assertIn("data-open-query-modal-close", rendered)
        self.assertIn("data-verification-item-filter", rendered)
        self.assertIn("Show all items", rendered)
        self.assertIn("Show items needing verification", rendered)
        self.assertIn('value="needs_verification"', rendered)
        self.assertIn("checked", rendered)
        self.assertIn("data-query-modal", rendered)
        self.assertIn('data-query-thread-url="/query-thread/"', rendered)
        self.assertIn("Mở Câu hỏi cho trường", rendered)
        self.assertIn("data-query-modal-comment-input", rendered)
        self.assertIn("data-query-modal-reply", rendered)
        self.assertIn("data-query-modal-resolved-wrap", rendered)
        self.assertIn("data-query-modal-resolved-input", rendered)
        self.assertIn("Is this Resolved?", rendered)
        self.assertIn("data-query-modal-reply-close", rendered)
        self.assertIn("data-query-modal-cancel", rendered)
        self.assertIn("Cancel Query", rendered)
        self.assertIn("data-query-modal-messages", rendered)
        self.assertIn("data-query-history-modal", rendered)
        self.assertIn("data-query-history-modal-list", rendered)
        self.assertIn("data-query-history-modal-messages", rendered)
        self.assertIn("data-query-history-modal-close", rendered)

    def test_subject_detail_renders_revert_verification_reason_modal(self):
        rendered = render_to_string(
            "subject/subject_detail.html",
            {
                "focused_forms": [{"id": 6, "title": "Vitals", "focus_url": "/subjects/1/?mode=verification&event=1&form=6"}],
                "event_navigation": [],
                "focused_event": {"id": 1},
                "focused_form": {"id": 6, "title": "Vitals"},
                "is_form_verification_mode": True,
                "is_subject_detail_viewonly_mode": False,
                "form_verification_review": SimpleNamespace(
                    header={
                        "event_name": "Visit 1",
                        "event_start_date": "05/18/2026",
                        "form_name": "Vitals",
                        "form_status": "submitted",
                        "form_version": "1",
                        "last_modified": "05/18/2026",
                    },
                    rows=[],
                ),
                "form_verification_verify_checked_url": "/api/verify-checked/",
                "form_verification_reopen_url": "",
                "form_verification_open_query_url": "",
                "form_verification_query_thread_url": "",
                "form_verification_fields_locked": False,
                "form_verification_query_actions_locked": False,
                "form_verification_show_actions_column": True,
                "form_verification_show_field_checkboxes": True,
                "form_verification_show_actions": True,
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

        self.assertIn("Reason for Revert Verification", rendered)
        self.assertIn("data-form-verification-revert-reason-modal", rendered)
        self.assertIn("data-form-verification-revert-reason-fields", rendered)
        self.assertIn("Date of Verify", rendered)
        self.assertIn("Field", rendered)
        self.assertIn("Reason", rendered)

    @staticmethod
    def _action_button_markup(rendered: str, marker: str) -> str:
        class_index = rendered.index(marker)
        button_start = rendered.rfind("<button", 0, class_index)
        button_end = rendered.index(">", class_index)
        return rendered[button_start : button_end + 1]

    def test_field_review_table_shows_checkbox_column_when_status_can_show_review_controls(self):
        rendered = self._render_field_review_table(show_checkboxes=True)

        self.assertIn('name="verify_field"', rendered)
        self.assertIn("subject-form-verification-review__col-check", rendered)
