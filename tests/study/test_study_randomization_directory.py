from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.services.study_randomization_directory import (
    StudyRandomizationDirectoryQueryService,
)


class StudyRandomizationDirectoryQueryServiceTests(SimpleTestCase):
    def test_slot_row_displays_randomization_id_separately_from_sequence(self):
        service = StudyRandomizationDirectoryQueryService(repository=object())
        slot = SimpleNamespace(
            pk=1,
            scheme_id=10,
            scheme=SimpleNamespace(code="NNG31_XOVER"),
            sequence_no=1,
            randomization_code="R-001",
            arm_id=11,
            arm=SimpleNamespace(arm_code="SEQ_E_N"),
            status="available",
            block_no=1,
            assigned_subject_id=None,
            assigned_at=None,
            void_reason=None,
            notes=None,
        )

        row = service._build_slot_row(slot)

        self.assertEqual(str(service.randomization_slot_headers[2]["label"]), "RANDOMIZATION ID")
        self.assertEqual(row["cells"][1]["value"], "1")
        self.assertEqual(row["cells"][2]["value"], "R-001")
