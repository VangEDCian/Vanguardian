from django.test import SimpleTestCase

from apps.subject.application import (
    SubjectFormVerificationFieldTemplateIdsTypeError,
    SubjectFormVerificationFieldTemplateIdsValueError,
    SubjectFormVerificationInvalidJsonError,
    SubjectFormVerificationRequestValidator,
)


class SubjectFormVerificationRequestValidatorTests(SimpleTestCase):
    def test_parse_checked_field_template_ids_returns_empty_list_when_missing(self):
        result = SubjectFormVerificationRequestValidator.parse_checked_field_template_ids("{}")

        self.assertEqual(result, [])

    def test_parse_checked_field_template_ids_normalizes_integer_values(self):
        result = SubjectFormVerificationRequestValidator.parse_checked_field_template_ids(
            b'{"field_template_ids": ["1", 2]}',
        )

        self.assertEqual(result, [1, 2])

    def test_parse_verify_checked_payload_normalizes_ids_and_reason(self):
        result = SubjectFormVerificationRequestValidator.parse_verify_checked_payload(
            b'{"field_template_ids": ["1", 2], "reason_text": "  Revert verification  ", '
            b'"review_page_entry_id": "  99  ", "review_entry_version": "  1  ", '
            b'"review_page_status": " submitted "}',
        )

        self.assertEqual(result["field_template_ids"], [1, 2])
        self.assertEqual(result["reason_text"], "Revert verification")
        self.assertEqual(result["review_page_entry_id"], "99")
        self.assertEqual(result["review_entry_version"], "1")
        self.assertEqual(result["review_page_status"], "submitted")

    def test_parse_checked_field_template_ids_rejects_invalid_json(self):
        with self.assertRaises(SubjectFormVerificationInvalidJsonError):
            SubjectFormVerificationRequestValidator.parse_checked_field_template_ids("{")

    def test_parse_checked_field_template_ids_rejects_non_list_ids(self):
        with self.assertRaises(SubjectFormVerificationFieldTemplateIdsTypeError):
            SubjectFormVerificationRequestValidator.parse_checked_field_template_ids(
                '{"field_template_ids": "1"}',
            )

    def test_parse_checked_field_template_ids_rejects_non_integer_values(self):
        with self.assertRaises(SubjectFormVerificationFieldTemplateIdsValueError):
            SubjectFormVerificationRequestValidator.parse_checked_field_template_ids(
                '{"field_template_ids": ["abc"]}',
            )

    def test_parse_reopen_reason_text_normalizes_reason(self):
        result = SubjectFormVerificationRequestValidator.parse_reopen_reason_text(
            b'{"reason_text": "  Reopen after review  "}',
        )

        self.assertEqual(result, "Reopen after review")

    def test_parse_reopen_reason_text_rejects_non_object_json(self):
        with self.assertRaises(SubjectFormVerificationInvalidJsonError):
            SubjectFormVerificationRequestValidator.parse_reopen_reason_text("[]")
