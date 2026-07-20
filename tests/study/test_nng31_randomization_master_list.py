import csv
import io
from types import SimpleNamespace

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.study.application.commands.import_randomization.types import (
    RandomizationImportValidationError,
)
from apps.study.application.services.import_randomization_commit import (
    _ensure_master_list_unlocked,
)
from apps.study.management.randomization_master_list import (
    REQUIRED_COLUMNS,
    parse_and_validate_nng31_master_list,
)


class Nng31RandomizationMasterListTests(SimpleTestCase):
    def test_generic_import_cannot_modify_a_locked_master_list_scheme(self):
        with self.assertRaises(RandomizationImportValidationError):
            _ensure_master_list_unlocked(
                scheme=SimpleNamespace(master_list_locked_at=object()),
                parsed_row=SimpleNamespace(row_number=2, identifier="NNG31_XOVER"),
            )

    def test_accepts_five_blocks_of_four_and_four_blocks_of_six(self):
        rows, checksum = parse_and_validate_nng31_master_list(
            content=self._valid_csv(),
            study=SimpleNamespace(code="NNG31"),
            scheme=SimpleNamespace(code="NNG31_XOVER", target_randomized_total=44),
            arms_by_code={"SEQ_E_N": object(), "SEQ_N_E": object()},
        )

        self.assertEqual(len(rows), 44)
        self.assertEqual(rows[0].randomization_code, "R-001")
        self.assertEqual(rows[-1].randomization_code, "R-044")
        self.assertEqual(len(checksum), 64)

    def test_rejects_an_unbalanced_block(self):
        content = self._valid_csv().decode("utf-8").replace(
            "NNG31_XOVER,R-004,4,1,SEQ_N_E",
            "NNG31_XOVER,R-004,4,1,SEQ_E_N",
        )

        with self.assertRaisesMessage(CommandError, "Block 1 is not balanced 1:1"):
            parse_and_validate_nng31_master_list(
                content=content.encode("utf-8"),
                study=SimpleNamespace(code="NNG31"),
                scheme=SimpleNamespace(code="NNG31_XOVER", target_randomized_total=44),
                arms_by_code={"SEQ_E_N": object(), "SEQ_N_E": object()},
            )

    def test_rejects_subject_identifier_as_randomization_identifier(self):
        content = self._valid_csv().decode("utf-8").replace("R-001", "NNG31-001")

        with self.assertRaisesMessage(CommandError, "R-001 through R-044"):
            parse_and_validate_nng31_master_list(
                content=content.encode("utf-8"),
                study=SimpleNamespace(code="NNG31"),
                scheme=SimpleNamespace(code="NNG31_XOVER", target_randomized_total=44),
                arms_by_code={"SEQ_E_N": object(), "SEQ_N_E": object()},
            )

    @staticmethod
    def _valid_csv():
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=REQUIRED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        sequence_no = 0
        for block_no, block_size in enumerate((4, 4, 4, 4, 4, 6, 6, 6, 6), start=1):
            for offset in range(block_size):
                sequence_no += 1
                writer.writerow(
                    {
                        "Scheme Code": "NNG31_XOVER",
                        "Randomization ID": f"R-{sequence_no:03}",
                        "Sequence No": sequence_no,
                        "Block No": block_no,
                        "Arm Code": "SEQ_E_N" if offset % 2 == 0 else "SEQ_N_E",
                    }
                )
        return output.getvalue().encode("utf-8")
