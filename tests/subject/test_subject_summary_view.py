from datetime import date, datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.subject_summary import (
    SubjectSummaryPeriodDTO,
    SubjectSummaryQueryService,
    SubjectSummarySnapshotDTO,
)


class SubjectSummaryViewTests(SimpleTestCase):
    def test_randomization_assignment_is_hidden_without_assignment_permission(self):
        snapshot = SubjectSummarySnapshotDTO(
            subject_id=20,
            study_id=1,
            study_code="NNG31",
            site_code="SITE01",
            screening_code="NNG31-S001",
            subject_code="NNG31-001",
            screening_date=datetime(2026, 6, 17),
            enrollment_is_enrolled=True,
            enrollment_status="enrolled",
            enrollment_date=date(2026, 6, 17),
            enrollment_status_datetime=datetime(2026, 6, 17),
            enrollment_reason_code="",
            enrollment_reason_text="",
            randomization_status="assigned",
            randomization_datetime=datetime(2026, 6, 17),
            randomization_number="R-001",
            randomization_scheme_code="NNG31_XOVER",
            randomization_arm_name="NANOKINE -> Eprex 4000 U",
            randomization_slot_sequence=1,
            randomization_event=None,
            periods=(
                SubjectSummaryPeriodDTO(1, "NANOKINE", "NNG31-001"),
                SubjectSummaryPeriodDTO(2, "EPREX_4000U", "R-NNG31-001"),
            ),
        )

        section = SubjectSummaryQueryService._build_randomization_section(
            snapshot,
            include_assignment=False,
        )
        labels = {item["label"] for item in section["items"]}

        self.assertNotIn("Randomization Number", labels)
        self.assertNotIn("Arm", labels)
        self.assertNotIn("Period 1 Treatment", labels)

    def test_randomization_assignment_shows_two_period_treatments_and_kit_codes(self):
        snapshot = SubjectSummarySnapshotDTO(
            subject_id=20,
            study_id=1,
            study_code="NNG31",
            site_code="SITE01",
            screening_code="NNG31-S001",
            subject_code="NNG31-001",
            screening_date=datetime(2026, 6, 17),
            enrollment_is_enrolled=True,
            enrollment_status="enrolled",
            enrollment_date=date(2026, 6, 17),
            enrollment_status_datetime=datetime(2026, 6, 17),
            enrollment_reason_code="",
            enrollment_reason_text="",
            randomization_status="assigned",
            randomization_datetime=datetime(2026, 6, 17),
            randomization_number="R-001",
            randomization_scheme_code="NNG31_XOVER",
            randomization_arm_name="NANOKINE -> Eprex 4000 U",
            randomization_slot_sequence=1,
            randomization_event=None,
            periods=(
                SubjectSummaryPeriodDTO(1, "NANOKINE", "NNG31-001"),
                SubjectSummaryPeriodDTO(2, "EPREX_4000U", "R-NNG31-001"),
            ),
        )

        section = SubjectSummaryQueryService._build_randomization_section(snapshot)
        rows = {item["label"]: item["value"] for item in section["items"]}

        self.assertEqual(rows["Randomization Number"], "R-001")
        self.assertEqual(rows["Period 1 Kit Code"], "NNG31-001")
        self.assertEqual(rows["Period 2 Kit Code"], "R-NNG31-001")
        self.assertIn("without re-screening", rows["Period 2 Instruction"])

    def test_enrollment_section_is_hidden_when_subject_is_not_enrolled(self):
        section = SubjectSummaryQueryService._build_enrollment_section(
            SubjectSummarySnapshotDTO(
                subject_id=20,
                study_id=1,
                study_code="NNG31",
                site_code="SITE01",
                screening_code="SCR-001",
                subject_code="",
                screening_date=datetime(2026, 6, 17),
                enrollment_is_enrolled=False,
                enrollment_status="eligible",
                enrollment_date=datetime(2026, 6, 17).date(),
                enrollment_status_datetime=datetime(2026, 6, 17),
                enrollment_reason_code="",
                enrollment_reason_text="",
                randomization_status="",
                randomization_datetime=None,
                randomization_number="",
                randomization_scheme_code="",
                randomization_arm_name="",
                randomization_slot_sequence=None,
                randomization_event=None,
            )
        )

        self.assertIsNone(section)

    def test_randomization_section_is_shown_when_randomization_stage_exists_without_assignment(self):
        event = SimpleNamespace(
            event_name="Randomization",
            status="open",
            opened_at=datetime(2026, 6, 17, 10, 30),
            planned_date=None,
        )

        section = SubjectSummaryQueryService._build_randomization_section(
            SubjectSummarySnapshotDTO(
                subject_id=20,
                study_id=1,
                study_code="NNG31",
                site_code="SITE01",
                screening_code="SCR-001",
                subject_code="",
                screening_date=datetime(2026, 6, 17),
                enrollment_is_enrolled=False,
                enrollment_status="eligible",
                enrollment_date=None,
                enrollment_status_datetime=None,
                enrollment_reason_code="",
                enrollment_reason_text="",
                randomization_status="",
                randomization_datetime=None,
                randomization_number="",
                randomization_scheme_code="",
                randomization_arm_name="",
                randomization_slot_sequence=None,
                randomization_event=event,
            )
        )

        self.assertIsNotNone(section)
        self.assertEqual(section["title"], "Randomization")
        self.assertIn(
            {"label": "Assignment Status", "value": "Not assigned", "is_temporal": False},
            section["items"],
        )

    def test_subject_stage_prefers_randomization_over_non_enrolled_enrollment(self):
        stage = SubjectSummaryQueryService._build_subject_stage_label(
            SubjectSummarySnapshotDTO(
                subject_id=20,
                study_id=1,
                study_code="NNG31",
                site_code="SITE01",
                screening_code="SCR-001",
                subject_code="",
                screening_date=datetime(2026, 6, 17),
                enrollment_is_enrolled=False,
                enrollment_status="eligible",
                enrollment_date=None,
                enrollment_status_datetime=None,
                enrollment_reason_code="",
                enrollment_reason_text="",
                randomization_status="",
                randomization_datetime=None,
                randomization_number="",
                randomization_scheme_code="",
                randomization_arm_name="",
                randomization_slot_sequence=None,
                randomization_event=SimpleNamespace(status="open"),
            )
        )

        self.assertEqual(stage, "Randomization")

    def test_build_section_filters_blank_values(self):
        section = SubjectSummaryQueryService._build_section(
            title="Screening",
            items=(
                ("Screening Code", "SCR-001"),
                ("Subject Code", ""),
                ("Screening Date", None),
            ),
        )

        self.assertEqual(
            section,
            {
                "title": "Screening",
                "items": [
                    {"label": "Screening Code", "value": "SCR-001", "is_temporal": False},
                ],
            },
        )

    def test_build_section_uses_date_format_for_date_objects(self):
        section = SubjectSummaryQueryService._build_section(
            title="Enrollment",
            items=(
                ("Enrollment Date", date(2026, 6, 17)),
                ("Status Datetime", datetime(2026, 6, 17, 10, 30)),
            ),
        )

        self.assertEqual(
            section["items"],
            [
                {
                    "label": "Enrollment Date",
                    "value": date(2026, 6, 17),
                    "is_temporal": True,
                    "format_name": "DATE_FORMAT",
                },
                {
                    "label": "Status Datetime",
                    "value": datetime(2026, 6, 17, 10, 30),
                    "is_temporal": True,
                    "format_name": "DATETIME_FORMAT",
                },
            ],
        )
