import json

from django.test import SimpleTestCase

from apps.datacapture.application.services.subject_export import (
    SubjectExportDataService,
)


class SubjectExportDataServiceTests(SimpleTestCase):
    field_specs = (
        {
            "token": "30:40",
            "binding_id": 30,
            "event_definition_id": 10,
            "crf_template_id": 20,
            "field_key": "AGE",
        },
    )

    def test_prefers_final_data_and_keeps_repeated_form_instances_as_rows(self):
        repository = _ExportDataRepositoryStub(
            rows=(
                self._row(
                    final_data=self._payload("900"),
                    current_entry_data=self._payload("draft"),
                    page_state_id=1,
                ),
                self._row(
                    final_data=self._payload("901"),
                    current_entry_data="",
                    page_state_id=2,
                ),
            )
        )

        values = SubjectExportDataService(repository=repository).read_values(
            study_id=1,
            site_id=2,
            subject_ids=(100,),
            field_specs=(
                {
                    **self.field_specs[0],
                    "is_repeatable_within_event": True,
                },
            ),
        )

        self.assertEqual(
            values,
            {
                100: (
                    {
                        "30:40": "900; 901",
                        "__export_visit_sort_key__": (0, 1, 0, 1, 1),
                    },
                )
            },
        )
        self.assertEqual(repository.calls[0]["site_id"], 2)

    def test_falls_back_to_current_entry_when_final_data_is_empty(self):
        repository = _ExportDataRepositoryStub(
            rows=(
                self._row(
                    final_data="{}",
                    current_entry_data=self._payload("draft"),
                    page_state_id=1,
                ),
            )
        )

        values = SubjectExportDataService(repository=repository).read_values(
            study_id=1,
            site_id=2,
            subject_ids=(100,),
            field_specs=self.field_specs,
        )

        self.assertEqual(
            {
                100: (
                    {
                        "30:40": "draft",
                        "__export_visit_sort_key__": (0, 1, 0, 1, 1),
                    },
                )
            },
            values,
        )

    def test_matches_legacy_page_state_without_binding_by_event_and_form(self):
        row = self._row(
            final_data=self._payload("42"),
            current_entry_data="",
            page_state_id=1,
        )
        row["event_form_binding_id"] = None
        repository = _ExportDataRepositoryStub(rows=(row,))

        values = SubjectExportDataService(repository=repository).read_values(
            study_id=1,
            site_id=2,
            subject_ids=(100,),
            field_specs=self.field_specs,
        )

        self.assertEqual(
            {
                100: (
                    {
                        "30:40": "42",
                        "__export_visit_sort_key__": (0, 1, 0, 1, 1),
                    },
                )
            },
            values,
        )

    def test_repeats_base_values_and_aligns_fields_from_each_form_instance(self):
        repeated_specs = (
            {
                "token": "31:41",
                "binding_id": 31,
                "event_definition_id": 10,
                "crf_template_id": 21,
                "field_key": "AETERM",
                "is_repeatable_within_event": True,
            },
            {
                "token": "31:42",
                "binding_id": 31,
                "event_definition_id": 10,
                "crf_template_id": 21,
                "field_key": "AESTDTC",
                "is_repeatable_within_event": True,
            },
        )
        repository = _ExportDataRepositoryStub(
            rows=(
                self._row(
                    final_data=self._payload("42"),
                    current_entry_data="",
                    page_state_id=1,
                ),
                self._row(
                    final_data=self._payload(
                        {
                            "AETERM": "Sốt",
                            "AESTDTC": "2026-06-18",
                        }
                    ),
                    current_entry_data="",
                    page_state_id=2,
                    binding_id=31,
                    crf_template_id=21,
                    repeat_index=1,
                ),
                self._row(
                    final_data=self._payload(
                        {
                            "AETERM": "Đau đầu",
                            "AESTDTC": "2026-06-15",
                        }
                    ),
                    current_entry_data="",
                    page_state_id=3,
                    binding_id=31,
                    crf_template_id=21,
                    repeat_index=2,
                ),
            )
        )

        values = SubjectExportDataService(repository=repository).read_values(
            study_id=1,
            site_id=2,
            subject_ids=(100,),
            field_specs=(
                {
                    **self.field_specs[0],
                    "is_repeatable_within_event": False,
                },
                *repeated_specs,
            ),
        )

        self.assertEqual(
            values,
            {
                100: (
                    {
                        "30:40": "42",
                        "31:41": "Sốt; Đau đầu",
                        "31:42": "2026-06-18; 2026-06-15",
                        "__export_visit_sort_key__": (0, 1, 0, 1, 1),
                    },
                )
            },
        )

    def test_decodes_radio_and_checkbox_values_to_option_labels(self):
        field_specs = (
            {
                "token": "30:40",
                "binding_id": 30,
                "event_definition_id": 10,
                "crf_template_id": 20,
                "field_key": "SEX",
                "is_repeatable_within_event": False,
                "control_type": "RADIO",
                "choice_labels": {"M": "Male", "F": "Female"},
            },
            {
                "token": "30:41",
                "binding_id": 30,
                "event_definition_id": 10,
                "crf_template_id": 20,
                "field_key": "SYMPTOMS",
                "is_repeatable_within_event": False,
                "control_type": "CHECKBOX",
                "choice_labels": {
                    "headache": "Headache",
                    "nausea": "Nausea",
                },
            },
        )
        repository = _ExportDataRepositoryStub(
            rows=(
                self._row(
                    final_data=self._payload(
                        {
                            "SEX": "F",
                            "SYMPTOMS": ["headache", "nausea", "other"],
                        }
                    ),
                    current_entry_data="",
                    page_state_id=1,
                ),
            )
        )

        values = SubjectExportDataService(repository=repository).read_values(
            study_id=1,
            site_id=2,
            subject_ids=(100,),
            field_specs=field_specs,
        )

        self.assertEqual(
            values,
            {
                100: (
                    {
                        "30:40": "Female",
                        "30:41": "Headache, Nausea, other",
                        "__export_visit_sort_key__": (0, 1, 0, 1, 1),
                    },
                )
            },
        )

    @staticmethod
    def _payload(value):
        items = value if isinstance(value, dict) else {"AGE": value}
        return json.dumps(
            {
                "format": "edc.form_data.v1",
                "groups": {
                    "DEMOGRAPHICS": {
                        "kind": "single",
                        "items": items,
                    }
                },
            }
        )

    @staticmethod
    def _row(
        *,
        final_data,
        current_entry_data,
        page_state_id,
        binding_id=30,
        crf_template_id=20,
        repeat_index=1,
    ):
        return {
            "id": page_state_id,
            "subject_id": 100,
            "event_form_binding_id": binding_id,
            "crf_template_id": crf_template_id,
            "visit__event_definition_id": 10,
            "visit__repeat_index": 1,
            "repeat_index": repeat_index,
            "final_data": final_data,
            "current_entry__data": current_entry_data,
        }


class _ExportDataRepositoryStub:
    def __init__(self, *, rows):
        self.rows = rows
        self.calls = []

    def list_page_state_rows(self, **kwargs):
        self.calls.append(kwargs)
        return self.rows
