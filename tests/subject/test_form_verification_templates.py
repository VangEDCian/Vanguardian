from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class FormVerificationTemplateTests(SimpleTestCase):
    def _render_field_review_table(self, *, show_checkboxes: bool) -> str:
        return render_to_string(
            "subject/includes/form_verification_field_review_table.html",
            {
                "LANGUAGE_CODE": "en",
                "form_verification_fields_locked": False,
                "form_verification_show_field_checkboxes": show_checkboxes,
                "form_verification_review": SimpleNamespace(
                    rows=[
                        {
                            "field_template_id": 11,
                            "is_checked": False,
                            "brief_description": "Field 1",
                            "display_value": "Value 1",
                            "open_query_count": 0,
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

    def test_field_review_table_shows_checkbox_column_when_status_can_show_review_controls(self):
        rendered = self._render_field_review_table(show_checkboxes=True)

        self.assertIn('name="verify_field"', rendered)
        self.assertIn("subject-form-verification-review__col-check", rendered)
