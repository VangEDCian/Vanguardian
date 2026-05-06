#!/usr/bin/env python3
"""
Generate bulk Study records for load testing.

Usage examples:
  python3 src/scripts/generate_studies.py
  python3 src/scripts/generate_studies.py --count 1000000 --batch-size 20000 --code-prefix PERF
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path


def _setup_django() -> None:
    script_dir = Path(__file__).resolve().parent
    src_dir = script_dir.parent
    server_dir = src_dir.parent

    sys.path.insert(0, str(src_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Vanguardian.settings")
    os.chdir(server_dir)

    import django  # noqa: PLC0415

    django.setup()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Study test data in bulk.")
    parser.add_argument("--count", type=int, default=1_000_000, help="How many studies to generate (default: 1000000).")
    parser.add_argument("--batch-size", type=int, default=10_000, help="Rows per bulk_create call (default: 10000).")
    parser.add_argument("--start-index", type=int, default=1, help="First sequence index (default: 1).")
    parser.add_argument("--code-prefix", type=str, default="STUDY", help="Prefix for study code (default: STUDY).")
    parser.add_argument("--actor-user-id", type=int, default=1, help="created_by_id / updated_by_id (default: 1).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned ranges only, do not insert.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.count <= 0:
        parser.error("--count must be > 0")
    if args.batch_size <= 0:
        parser.error("--batch-size must be > 0")
    if args.start_index <= 0:
        parser.error("--start-index must be > 0")

    _setup_django()

    from django.db import transaction  # noqa: PLC0415
    from django.utils import timezone  # noqa: PLC0415

    from apps.study.infrastructure.persistence.models.study import Study  # noqa: PLC0415

    start = args.start_index
    end = args.start_index + args.count - 1
    print(
        f"[generate_studies] start={start:,} end={end:,} count={args.count:,} "
        f"batch_size={args.batch_size:,} prefix={args.code_prefix}",
    )

    total_inserted = 0
    began_at = time.perf_counter()

    for batch_start in range(start, end + 1, args.batch_size):
        batch_end = min(batch_start + args.batch_size - 1, end)
        batch_size = batch_end - batch_start + 1

        if args.dry_run:
            print(f"[dry-run] batch {batch_start:,}..{batch_end:,} ({batch_size:,})")
            total_inserted += batch_size
            continue

        now = timezone.now()
        rows = []
        for i in range(batch_start, batch_end + 1):
            code = f"{args.code_prefix}-{i:07d}"
            start_date = date(2026, 1, 1) + timedelta(days=i % 365)
            end_date = start_date + timedelta(days=180)

            rows.append(
                Study(
                    code=code,
                    name=f"Generated Study {i}",
                    sponsor=f"Sponsor {i % 1000}",
                    description=f"Generated load-test study {i}",
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                    created_by_id=args.actor_user_id,
                    updated_by_id=args.actor_user_id,
                ),
            )

        with transaction.atomic():
            Study.objects.bulk_create(rows, batch_size=args.batch_size)

        total_inserted += batch_size
        elapsed = time.perf_counter() - began_at
        rate = int(total_inserted / elapsed) if elapsed > 0 else 0
        print(
            f"[generate_studies] inserted={total_inserted:,}/{args.count:,} "
            f"({total_inserted / args.count:.1%}) rate={rate:,} rows/s",
        )

    total_elapsed = time.perf_counter() - began_at
    print(
        f"[generate_studies] done inserted={total_inserted:,} "
        f"elapsed={total_elapsed:.1f}s",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
