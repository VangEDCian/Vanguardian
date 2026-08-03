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

    def test_prefers_final_data_and_aggregates_repeated_values(self):
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
            field_specs=self.field_specs,
        )

        self.assertEqual(values, {100: {"30:40": '["900", "901"]'}})
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

        self.assertEqual(values, {100: {"30:40": "draft"}})

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

        self.assertEqual(values, {100: {"30:40": "42"}})

    @staticmethod
    def _payload(value):
        return json.dumps(
            {
                "format": "edc.form_data.v1",
                "groups": {
                    "DEMOGRAPHICS": {
                        "kind": "single",
                        "items": {"AGE": value},
                    }
                },
            }
        )

    @staticmethod
    def _row(*, final_data, current_entry_data, page_state_id):
        return {
            "id": page_state_id,
            "subject_id": 100,
            "event_form_binding_id": 30,
            "crf_template_id": 20,
            "visit__event_definition_id": 10,
            "visit__repeat_index": 1,
            "repeat_index": 1,
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
