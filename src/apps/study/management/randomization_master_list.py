import csv
import hashlib
import io
from collections import Counter, defaultdict
from dataclasses import dataclass

from django.core.management.base import CommandError

EXPECTED_BLOCK_SIZES = (4, 4, 4, 4, 4, 6, 6, 6, 6)
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

    if len(rows) != 44 or scheme.target_randomized_total != 44:
        raise CommandError("NNG31 master list and scheme target must both contain exactly 44 allocations.")
    if str(study.code).strip().upper() != "NNG31" or scheme.code != "NNG31_XOVER":
        raise CommandError("This command only accepts study NNG31 and scheme NNG31_XOVER.")
    if set(arms_by_code) != {"SEQ_E_N", "SEQ_N_E"}:
        raise CommandError("NNG31_XOVER must have exactly the active arms SEQ_E_N and SEQ_N_E.")

    expected_sequences = list(range(1, 45))
    if [row.sequence_no for row in rows] != expected_sequences:
        raise CommandError("Sequence No must be ordered, unique, and contiguous from 1 through 44.")
    expected_codes = [f"R-{sequence_no:03}" for sequence_no in expected_sequences]
    if [row.randomization_code for row in rows] != expected_codes:
        raise CommandError("Randomization ID must be ordered exactly from R-001 through R-044.")
    if any(row.scheme_code != scheme.code for row in rows):
        raise CommandError(f"Every Scheme Code must be {scheme.code}.")
    if any(row.arm_code not in arms_by_code for row in rows):
        raise CommandError("Every Arm Code must reference an active NNG31 crossover arm.")

    rows_by_block = defaultdict(list)
    for row in rows:
        rows_by_block[row.block_no].append(row)
    if sorted(rows_by_block) != list(range(1, 10)):
        raise CommandError("Block No must be contiguous from 1 through 9.")
    expected_block_numbers = [
        block_no
        for block_no, block_size in enumerate(EXPECTED_BLOCK_SIZES, start=1)
        for _offset in range(block_size)
    ]
    if [row.block_no for row in rows] != expected_block_numbers:
        raise CommandError("Each block must occupy one contiguous sequence range in block order.")
    actual_sizes = tuple(len(rows_by_block[block_no]) for block_no in range(1, 10))
    if actual_sizes != EXPECTED_BLOCK_SIZES:
        raise CommandError("NNG31 requires five blocks of 4 followed by four blocks of 6.")
    for block_no, block_rows in rows_by_block.items():
        counts = Counter(row.arm_code for row in block_rows)
        expected_per_arm = len(block_rows) // 2
        if any(counts[arm_code] != expected_per_arm for arm_code in arms_by_code):
            raise CommandError(f"Block {block_no} is not balanced 1:1.")

    totals = Counter(row.arm_code for row in rows)
    if totals != Counter({"SEQ_E_N": 22, "SEQ_N_E": 22}):
        raise CommandError("NNG31 master list must allocate exactly 22 subjects to each sequence.")
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
