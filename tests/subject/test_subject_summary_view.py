from datetime import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.subject_summary import (
    SubjectSummaryQueryService,
    SubjectSummarySnapshotDTO,
)


class SubjectSummaryViewTests(SimpleTestCase):
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
