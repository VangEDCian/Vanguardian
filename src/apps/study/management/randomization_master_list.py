import csv
import hashlib
import io
from collections import Counter
from dataclasses import dataclass

from django.core.management.base import CommandError

from apps.study.domain import (
    RandomizationCodeConfigurationError,
    format_scheme_randomization_code,
)

REQUIRED_COLUMNS = (
    "Scheme Code",
    "Randomization ID",
    "Sequence No",
    "Block No",
    "Arm Code",
)


@dataclass(frozen=True)
class MasterListRow:
    scheme_code: str
    randomization_code: str
    sequence_no: int
    block_no: int
    arm_code: str


def parse_and_validate_nng31_master_list(*, content: bytes, study, scheme, arms_by_code):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CommandError("Master-list CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
        raise CommandError(f"CSV columns must be exactly: {', '.join(REQUIRED_COLUMNS)}.")

    rows = []
    for line_no, raw in enumerate(reader, start=2):
        try:
            row = MasterListRow(
                scheme_code=str(raw["Scheme Code"] or "").strip(),
                randomization_code=str(raw["Randomization ID"] or "").strip(),
                sequence_no=int(raw["Sequence No"]),
                block_no=int(raw["Block No"]),
                arm_code=str(raw["Arm Code"] or "").strip(),
            )
        except (TypeError, ValueError) as exc:
            raise CommandError(f"Line {line_no} has an invalid sequence or block number.") from exc
        rows.append(row)

    expected_total = int(scheme.target_randomized_total or 0)
    if len(rows) != expected_total:
        raise CommandError(
            "Master list must contain exactly the scheme target of "
            f"{expected_total} allocations."
        )
    if str(study.code).strip().upper() != "NNG31":
        raise CommandError("This command only accepts study NNG31.")
    if len(arms_by_code) != 2:
        raise CommandError("The NNG31 crossover scheme must have exactly two active arms.")

    expected_sequences = list(range(1, expected_total + 1))
    if [row.sequence_no for row in rows] != expected_sequences:
        raise CommandError(
            "Sequence No must be ordered, unique, and contiguous from 1 through "
            f"{expected_total}."
        )
    try:
        expected_codes = [
            format_scheme_randomization_code(scheme=scheme, sequence_no=sequence_no)
            for sequence_no in expected_sequences
        ]
    except RandomizationCodeConfigurationError as exc:
        raise CommandError(str(exc)) from exc
    if [row.randomization_code for row in rows] != expected_codes:
        raise CommandError(
            "Randomization ID must be ordered exactly from "
            f"{expected_codes[0]} through {expected_codes[-1]}."
        )
    if any(row.scheme_code != scheme.code for row in rows):
        raise CommandError(f"Every Scheme Code must be {scheme.code}.")
    if any(row.arm_code not in arms_by_code for row in rows):
        raise CommandError("Every Arm Code must reference an active NNG31 crossover arm.")

    totals = Counter(row.arm_code for row in rows)
    expected_per_arm = expected_total // 2
    if expected_total % 2 or totals != Counter(
        {arm_code: expected_per_arm for arm_code in arms_by_code}
    ):
        raise CommandError(
            "Master list must allocate subjects equally between the two sequences."
        )
    return rows, hashlib.sha256(content).hexdigest()


def validate_stored_nng31_slots(*, study, scheme, arms_by_code, slots):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=REQUIRED_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for slot in slots:
        writer.writerow(
            {
                "Scheme Code": scheme.code,
                "Randomization ID": slot.randomization_code,
                "Sequence No": slot.sequence_no,
                "Block No": slot.block_no,
                "Arm Code": slot.arm.arm_code,
            }
        )
    rows, _checksum = parse_and_validate_nng31_master_list(
        content=content.getvalue().encode("utf-8"),
        study=study,
        scheme=scheme,
        arms_by_code=arms_by_code,
    )
    return rows
