from django.test import SimpleTestCase

from apps.core.form_data_document import (
    FORM_DATA_FORMAT,
    FieldTemplateSnapshot,
    FormDataNormalizationError,
    FormTemplateSnapshot,
    SectionTemplateSnapshot,
    build_field_path,
    flatten_form_data_for_export,
    get_field_value,
    iter_field_values,
    normalize_form_data,
    set_field_value,
)


def _snapshot():
    return FormTemplateSnapshot(
        form_code="FORM_A",
        form_version="1.0",
        sections=[
            SectionTemplateSnapshot(
                section_code="PRESENCE",
                is_repeatable=False,
                fields=[
                    FieldTemplateSnapshot(
                        field_key="HAS_ANY_MEDICAL_HISTORY",
                        section_code="PRESENCE",
                    )
                ],
            ),
            SectionTemplateSnapshot(
                section_code="ENTRIES",
                is_repeatable=True,
                fields=[
                    FieldTemplateSnapshot(
                        field_key="MEDICAL_HISTORY_TERM",
                        section_code="ENTRIES",
                    )
                ],
            ),
        ],
    )


class FormDataDocumentTests(SimpleTestCase):
    def test_normalize_none_returns_empty_canonical_doc(self):
        doc = normalize_form_data(None, template_snapshot=_snapshot(), entry_version=1)

        self.assertEqual(doc["format"], FORM_DATA_FORMAT)
        self.assertNotIn("form_code", doc)
        self.assertNotIn("form_version", doc)
        self.assertNotIn("entry_version", doc)
        self.assertEqual(doc["groups"], {})

    def test_normalize_canonical_preserves_semantic_values(self):
        raw = {
            "format": FORM_DATA_FORMAT,
            "form_code": "FORM_A",
            "form_version": "1.0",
            "entry_version": "v1",
            "groups": {"PRESENCE": {"kind": "single", "items": {"HAS_ANY_MEDICAL_HISTORY": True}}},
        }

        doc = normalize_form_data(raw, template_snapshot=_snapshot())

        self.assertEqual(doc["groups"]["PRESENCE"]["items"]["HAS_ANY_MEDICAL_HISTORY"], True)
        self.assertNotIn("form_code", doc)

    def test_normalize_can_include_metadata_for_report_context(self):
        doc = normalize_form_data(
            None,
            template_snapshot=_snapshot(),
            entry_version=1,
            include_metadata=True,
        )

        self.assertEqual(doc["form_code"], "FORM_A")
        self.assertEqual(doc["form_version"], "1.0")
        self.assertEqual(doc["entry_version"], "1")

    def test_legacy_non_repeatable_field_maps_to_single_group(self):
        doc = normalize_form_data(
            {"HAS_ANY_MEDICAL_HISTORY": True},
            template_snapshot=_snapshot(),
            strict=True,
        )

        self.assertEqual(
            doc["groups"]["PRESENCE"],
            {"kind": "single", "items": {"HAS_ANY_MEDICAL_HISTORY": True}},
        )

    def test_legacy_repeatable_field_creates_stable_first_row(self):
        doc = normalize_form_data(
            {"MEDICAL_HISTORY_TERM": "Dị ứng penicillin"},
            template_snapshot=_snapshot(),
            strict=True,
        )

        self.assertEqual(doc["groups"]["ENTRIES"]["kind"], "repeatable")
        self.assertEqual(
            doc["groups"]["ENTRIES"]["rows"][0],
            {
                "row_key": "row_001",
                "row_no": 1,
                "items": {"MEDICAL_HISTORY_TERM": "Dị ứng penicillin"},
            },
        )

    def test_legacy_unmapped_field_raises_in_strict_mode(self):
        with self.assertRaises(FormDataNormalizationError) as ctx:
            normalize_form_data({"UNKNOWN_FIELD": "x"}, template_snapshot=_snapshot(), strict=True)

        self.assertEqual(ctx.exception.unmapped_fields, ("UNKNOWN_FIELD",))

    def test_get_field_value_reads_single_group(self):
        doc = normalize_form_data({"HAS_ANY_MEDICAL_HISTORY": True}, template_snapshot=_snapshot())

        value = get_field_value(doc, section_code="PRESENCE", field_key="HAS_ANY_MEDICAL_HISTORY")

        self.assertIs(value, True)

    def test_get_field_value_reads_repeatable_group_by_row_key(self):
        doc = normalize_form_data({"MEDICAL_HISTORY_TERM__repeat_2": "Asthma"}, template_snapshot=_snapshot())

        value = get_field_value(
            doc,
            section_code="ENTRIES",
            field_key="MEDICAL_HISTORY_TERM",
            row_key="row_002",
        )

        self.assertEqual(value, "Asthma")

    def test_set_field_value_writes_single_group(self):
        doc = set_field_value({}, section_code="PRESENCE", field_key="HAS_ANY_MEDICAL_HISTORY", value=False)

        self.assertIs(doc["groups"]["PRESENCE"]["items"]["HAS_ANY_MEDICAL_HISTORY"], False)

    def test_set_field_value_writes_repeatable_group(self):
        doc = set_field_value(
            {},
            section_code="ENTRIES",
            field_key="MEDICAL_HISTORY_TERM",
            value="Asthma",
            row_no=2,
        )

        self.assertEqual(doc["groups"]["ENTRIES"]["rows"][0]["row_key"], "row_002")
        self.assertEqual(doc["groups"]["ENTRIES"]["rows"][0]["items"]["MEDICAL_HISTORY_TERM"], "Asthma")

    def test_iter_field_values_returns_canonical_path(self):
        doc = normalize_form_data({"MEDICAL_HISTORY_TERM": "Asthma"}, template_snapshot=_snapshot())

        refs = list(iter_field_values(doc))

        self.assertEqual(refs[0].path, "groups.ENTRIES.rows[row_001].items.MEDICAL_HISTORY_TERM")

    def test_flatten_form_data_for_export_preserves_single_value(self):
        doc = normalize_form_data({"HAS_ANY_MEDICAL_HISTORY": True}, template_snapshot=_snapshot())

        self.assertEqual(flatten_form_data_for_export(doc), {"HAS_ANY_MEDICAL_HISTORY": True})

    def test_flatten_form_data_for_export_keeps_repeat_row_context(self):
        doc = normalize_form_data({"MEDICAL_HISTORY_TERM": "Asthma"}, template_snapshot=_snapshot())

        self.assertEqual(flatten_form_data_for_export(doc), {"ENTRIES[1].MEDICAL_HISTORY_TERM": "Asthma"})

    def test_build_field_path_uses_row_key_for_repeatable_fields(self):
        self.assertEqual(
            build_field_path("ENTRIES", "MEDICAL_HISTORY_TERM", row_key="row_001"),
            "groups.ENTRIES.rows[row_001].items.MEDICAL_HISTORY_TERM",
        )
